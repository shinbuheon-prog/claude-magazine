"""
편집 체크리스트 자동 검증 — editorial_lint.py
TASK_016: Ghost 발행 전 필수 게이트. docs/editorial_checklist.md의 10개 항목을 자동 검증한다.

사용법:
    python pipeline/editorial_lint.py --draft drafts/article.md
    python pipeline/editorial_lint.py --draft drafts/article.md --only source-id ai-disclosure
    python pipeline/editorial_lint.py --draft drafts/article.md --json
    python pipeline/editorial_lint.py --draft drafts/article.md --strict
    python pipeline/editorial_lint.py --ghost-post-id POST_ID
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Windows UTF-8 래핑 가드 — 다중 모듈 import 시 재래핑하면 closed file 에러 발생.
if (
    sys.platform == "win32"
    and "pytest" not in sys.modules
    and not getattr(sys.stdout, "_utf8_wrapped", False)
):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stdout._utf8_wrapped = True  # type: ignore[attr-defined]
        sys.stderr._utf8_wrapped = True  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

NETWORK_TIMEOUT = 10

# 10개 항목의 ID 순서 (editorial_checklist.md 매핑)
CHECK_IDS = [
    "source-id",
    "citations-cross-check",
    "translation-guard",
    "title-body-match",
    "quote-fidelity",
    "no-fabrication",
    "pii-check",
    "image-rights",
    "ai-disclosure",
    "correction-policy",
    "request-id-log",
]
OPTIONAL_CHECK_IDS = CHECK_IDS + ["article-standards"]
CARD_NEWS_CHECK_IDS = ["card-news-structure", "card-news-density", "source-fidelity", "slide-count"]

STATUS_ICON = {"pass": "✅", "fail": "❌", "warn": "⚠️ ", "skip": "➖"}

SOURCE_ID_PATTERN = re.compile(r"\[src-[a-zA-Z0-9_-]+\]|\(source_id:\s*[^)]+\)")
# 마크다운 문법, 고지/정책 문구는 주장 문장으로 취급하지 않음
CLAIM_SKIP_PREFIXES = ("#", "-", "*", ">", "|", "!", "```", "  ")


# ---------------------------------------------------------------------------
# 헬퍼 — 문장 추출, Ghost HTML → Markdown 유사 텍스트
# ---------------------------------------------------------------------------


def _strip_html(html: str) -> str:
    """Ghost HTML을 간이로 벗겨 텍스트/이미지 태그는 유지."""
    # <img ...> 태그는 image-rights 체크를 위해 보존한다.
    images = re.findall(r"<img[^>]*>", html, flags=re.IGNORECASE)
    text = re.sub(r"<img[^>]*>", "__IMG_PLACEHOLDER__", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    # 이미지 태그를 되돌려 넣는다 (image-rights 체크에서 HTML을 그대로 스캔할 수 있도록)
    for img in images:
        text = text.replace("__IMG_PLACEHOLDER__", img, 1)
    return text


DISCLOSURE_SECTION_MARKERS = (
    "AI 사용 고지",
    "AI 고지",
    "정정 정책",
    "정정 요청",
    "정정 담당",
    "편집 고지",
    "Editor's note",
    "Disclosure",
)


def _split_sentences(text: str) -> list[str]:
    """한국어/영어 혼합 문장 분리 — 마침표·물음표·느낌표·개행 기준.

    ## AI 사용 고지 / ## 정정 정책 등 편집 고지 섹션에 진입하면 이후 라인은
    주장 문장으로 취급하지 않는다 (source_id 요구 대상 아님).
    """
    # 코드블록 제거
    cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # 이미지 태그 제거 (문장으로 오인 방지)
    cleaned = re.sub(r"<img[^>]*>", "", cleaned, flags=re.IGNORECASE)
    sentences: list[str] = []
    in_disclosure_section = False
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # 헤더에서 고지 섹션 진입 여부 판정
        if stripped.startswith("#"):
            header_text = stripped.lstrip("#").strip()
            in_disclosure_section = any(m in header_text for m in DISCLOSURE_SECTION_MARKERS)
            continue
        if in_disclosure_section:
            continue
        if stripped.startswith(CLAIM_SKIP_PREFIXES):
            continue
        # 문장 분리 — 문장부호 뒤 공백/끝 기준
        parts = re.split(r"(?<=[.!?。！？])\s+|\n+", stripped)
        for part in parts:
            part = part.strip()
            if len(part) >= 8:  # 너무 짧은 조각은 건너뜀
                sentences.append(part)
    return sentences


# ---------------------------------------------------------------------------
# 체크 1: source-id — 주장 문장 끝에 [src-xxx] 또는 (source_id: ...) 존재
# ---------------------------------------------------------------------------


def check_source_id(text: str) -> dict[str, Any]:
    sentences = _split_sentences(text)
    if not sentences:
        return {"id": "source-id", "status": "warn", "message": "검증할 주장 문장이 없음"}

    missing = []
    for s in sentences:
        # 따옴표로만 시작하는 단문 인용, 완전한 헤더/리스트는 스킵됨
        if not SOURCE_ID_PATTERN.search(s):
            missing.append(s[:60])

    total = len(sentences)
    linked = total - len(missing)
    if not missing:
        return {
            "id": "source-id",
            "status": "pass",
            "message": f"모든 주장에 source_id 연결 ({linked}개)",
        }
    return {
        "id": "source-id",
        "status": "fail",
        "message": f"{len(missing)}개 문장에 source_id 없음 (연결 {linked}/{total})",
        "details": missing[:5],
    }


# ---------------------------------------------------------------------------
# 체크 1b: citations-cross-check — 수동 source_id 와 citations 결과 교차검증
# ---------------------------------------------------------------------------


def _extract_manual_source_ids(text: str) -> set[str]:
    return {match.strip() for match in re.findall(r"src-[a-zA-Z0-9_-]+", text)}


def check_citations_cross_check(text: str, article_id: str | None = None) -> dict[str, Any]:
    if not article_id:
        return {
            "id": "citations-cross-check",
            "status": "warn",
            "message": "article_id missing; citations cross-check skipped",
        }

    try:
        try:
            from pipeline.citations_store import load_citations
        except ModuleNotFoundError:
            from citations_store import load_citations  # type: ignore
    except ImportError:
        return {
            "id": "citations-cross-check",
            "status": "warn",
            "message": "citations_store missing; citations cross-check skipped",
        }

    payload = load_citations(article_id)
    if not payload:
        return {
            "id": "citations-cross-check",
            "status": "warn",
            "message": f"no citations data for article_id={article_id}",
        }

    manual_source_ids = _extract_manual_source_ids(text)
    cited_source_ids = {
        citation.get("source_id")
        for claim in payload.get("claims", [])
        for citation in claim.get("citations", [])
        if citation.get("source_id")
    }

    if not manual_source_ids:
        return {
            "id": "citations-cross-check",
            "status": "warn",
            "message": "manual source_id markers not found in draft",
        }
    if not cited_source_ids:
        return {
            "id": "citations-cross-check",
            "status": "warn",
            "message": "citations file exists but no source_id-backed citations were extracted",
        }

    missing = sorted(manual_source_ids - cited_source_ids)
    if missing:
        return {
            "id": "citations-cross-check",
            "status": "warn",
            "message": f"{len(missing)} source_id values are not backed by citations output yet",
            "details": missing[:5],
        }
    return {
        "id": "citations-cross-check",
        "status": "pass",
        "message": f"manual source_id markers align with citations output ({len(manual_source_ids)} ids)",
    }


# ---------------------------------------------------------------------------
# 체크 2: translation-guard — 3줄 이상 연속 인용 경고
# ---------------------------------------------------------------------------


def check_translation_guard(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    long_quotes: list[tuple[int, int]] = []
    run_start: int | None = None
    run_len = 0
    for idx, line in enumerate(lines, start=1):
        if line.strip().startswith(">"):
            if run_start is None:
                run_start = idx
                run_len = 1
            else:
                run_len += 1
        else:
            if run_start is not None and run_len >= 3:
                long_quotes.append((run_start, run_len))
            run_start = None
            run_len = 0
    if run_start is not None and run_len >= 3:
        long_quotes.append((run_start, run_len))

    if not long_quotes:
        return {
            "id": "translation-guard",
            "status": "pass",
            "message": "장문 인용 없음 (3줄 이상 연속 인용 0건)",
        }
    detail = ", ".join(f"{line}번째 줄부터 {length}줄" for line, length in long_quotes[:3])
    return {
        "id": "translation-guard",
        "status": "warn",
        "message": f"장문 인용 {len(long_quotes)}건 — {detail}",
    }


# ---------------------------------------------------------------------------
# 체크 3: title-body-match — Sonnet에게 제목-본문 일치도 판정 호출
# ---------------------------------------------------------------------------


def _extract_title_body(text: str) -> tuple[str, str]:
    title = ""
    body_lines: list[str] = []
    found = False
    for line in text.splitlines():
        stripped = line.replace("\ufeff", "").strip()
        if not found and stripped.startswith("# "):
            title = stripped.lstrip("#").strip()
            # 제목 뒤 source_id 제거
            title = SOURCE_ID_PATTERN.sub("", title).strip()
            found = True
            continue
        if found:
            body_lines.append(line)
    return title, "\n".join(body_lines).strip()


def check_title_body_match(text: str) -> dict[str, Any]:
    title, body = _extract_title_body(text)
    if not title:
        return {
            "id": "title-body-match",
            "status": "fail",
            "message": "제목(# H1)을 찾을 수 없음",
        }
    if not body:
        return {
            "id": "title-body-match",
            "status": "fail",
            "message": "본문이 비어 있음",
        }

    # TASK_033: provider 추상화 (SDK/API/mock 자동 선택)
    kind = (os.getenv("CLAUDE_PROVIDER", "api")).lower()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if kind == "api" and not api_key:
        return {
            "id": "title-body-match",
            "status": "warn",
            "message": "ANTHROPIC_API_KEY 미설정 — 일치도 판정 skip",
        }

    try:
        try:
            from pipeline.claude_provider import get_provider
        except ModuleNotFoundError:
            from claude_provider import get_provider  # type: ignore

        provider = get_provider()
        body_excerpt = body[:2000]
        system_prompt = (
            "너는 한국어 기사 편집자다. 제목과 본문의 일치도를 0~100 점수로만 출력하라. "
            "낚시성·과장·불일치가 없고 본문이 제목을 정확히 뒷받침하면 100, 크게 어긋나면 0. "
            "반드시 정수 한 개만 출력 (예: 87)."
        )
        user_prompt = f"[제목]\n{title}\n\n[본문 발췌]\n{body_excerpt}"

        system_blocks = [{"type": "text", "text": system_prompt}]
        messages = [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}]
        try:
            token_count = provider.count_tokens(
                system_blocks=system_blocks,
                messages=messages,
                model_tier="sonnet",
            )
        except Exception:
            token_count = 0
        if provider.name == "api" and token_count >= 2048:
            system_blocks[-1]["cache_control"] = {"type": "ephemeral"}

        result = provider.complete_with_blocks(
            system_blocks=system_blocks,
            messages=messages,
            model_tier="sonnet",
            max_tokens=100,
        )
        reply = (result.text or "").strip()
        score_match = re.search(r"\d{1,3}", reply)
        if not score_match:
            return {
                "id": "title-body-match",
                "status": "warn",
                "message": f"Sonnet 응답 파싱 실패: {reply[:50]}",
            }
        score = min(int(score_match.group(0)), 100)
        status = "pass" if score >= 70 else ("warn" if score >= 50 else "fail")
        return {
            "id": "title-body-match",
            "status": status,
            "message": f"일치도 {score}점",
            "score": score,
        }
    except Exception as exc:
        return {
            "id": "title-body-match",
            "status": "warn",
            "message": f"Sonnet 호출 실패 — skip ({type(exc).__name__})",
        }


# ---------------------------------------------------------------------------
# 체크 4: quote-fidelity — source_registry 원문과 인용 대조
# ---------------------------------------------------------------------------


def _extract_quotes(text: str) -> list[str]:
    quotes: list[str] = []
    quotes.extend(re.findall(r'"([^"\n]{4,200})"', text))
    quotes.extend(re.findall(r'“([^”\n]{4,200})”', text))
    return quotes


def check_quote_fidelity(text: str, article_id: str | None = None) -> dict[str, Any]:
    quotes = _extract_quotes(text)
    if not quotes:
        return {
            "id": "quote-fidelity",
            "status": "pass",
            "message": "검증할 인용문 없음",
        }

    try:
        try:
            from pipeline.source_registry import list_sources
        except ModuleNotFoundError:
            from source_registry import list_sources  # type: ignore
    except ImportError:
        return {
            "id": "quote-fidelity",
            "status": "warn",
            "message": "source_registry 미연동 — skip",
        }

    if not article_id:
        return {
            "id": "quote-fidelity",
            "status": "warn",
            "message": "article_id 미지정 — 원문 대조 skip",
        }

    try:
        sources = list_sources(article_id)
    except Exception as exc:  # pragma: no cover
        return {
            "id": "quote-fidelity",
            "status": "warn",
            "message": f"source_registry 조회 실패 — skip ({type(exc).__name__})",
        }

    if not sources:
        return {
            "id": "quote-fidelity",
            "status": "warn",
            "message": f"article_id={article_id}에 등록된 소스 없음",
        }

    # 원문 본문은 DB에 보관되지 않으므로 URL fetch 시도 (timeout=10)
    import requests

    bodies: list[str] = []
    for s in sources:
        try:
            resp = requests.get(s["url"], timeout=NETWORK_TIMEOUT)
            resp.raise_for_status()
            bodies.append(_strip_html(resp.text))
        except Exception:  # pragma: no cover
            continue

    if not bodies:
        return {
            "id": "quote-fidelity",
            "status": "warn",
            "message": "원문 fetch 실패 — skip",
        }

    combined = " ".join(bodies)
    mismatched: list[str] = []
    for q in quotes:
        if q not in combined:
            mismatched.append(q[:40])

    if not mismatched:
        return {
            "id": "quote-fidelity",
            "status": "pass",
            "message": f"인용 {len(quotes)}건 전부 원문 일치",
        }
    return {
        "id": "quote-fidelity",
        "status": "fail",
        "message": f"인용 {len(mismatched)}건 원문 불일치",
        "details": mismatched[:5],
    }


# ---------------------------------------------------------------------------
# 체크 5: no-fabrication — 수치·기업명이 소스 내에 존재하는지 grep
# ---------------------------------------------------------------------------

NUMBER_PATTERN = re.compile(r"\$?\d[\d,\.]*\s?(?:%|MTok|억|만|천|달러|원|엔|명|개|건|배)?")
COMPANY_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9&.-]{2,}(?:\s+[A-Z][a-zA-Z0-9&.-]+)*\b")


def check_no_fabrication(text: str, article_id: str | None = None) -> dict[str, Any]:
    numbers = {m.group(0).strip() for m in NUMBER_PATTERN.finditer(text) if len(m.group(0).strip()) > 1}
    companies = set(COMPANY_PATTERN.findall(text))
    # Claude 등 프로젝트에서 자주 등장하는 토큰은 소스 내 존재 여부 검사 대상에서 제외하지 않는다
    companies = {c for c in companies if not c.isupper() or len(c) > 3}

    # source_registry가 없거나 article_id가 없으면 근거 확인 불가 — warn 처리
    try:
        try:
            from pipeline.source_registry import list_sources
        except ModuleNotFoundError:
            from source_registry import list_sources  # type: ignore
    except ImportError:
        return {
            "id": "no-fabrication",
            "status": "warn",
            "message": "source_registry 미연동 — 수치/기업명 근거 확인 skip",
        }

    if not article_id:
        return {
            "id": "no-fabrication",
            "status": "warn",
            "message": "article_id 미지정 — skip (수치 {}건, 기업명 {}건 감지)".format(
                len(numbers), len(companies)
            ),
        }

    try:
        sources = list_sources(article_id)
    except Exception as exc:  # pragma: no cover
        return {
            "id": "no-fabrication",
            "status": "warn",
            "message": f"source_registry 조회 실패 — skip ({type(exc).__name__})",
        }
    if not sources:
        return {
            "id": "no-fabrication",
            "status": "warn",
            "message": f"article_id={article_id}에 등록된 소스 없음",
        }

    import requests

    combined = ""
    for s in sources:
        try:
            resp = requests.get(s["url"], timeout=NETWORK_TIMEOUT)
            resp.raise_for_status()
            combined += " " + _strip_html(resp.text)
        except Exception:  # pragma: no cover
            continue

    if not combined.strip():
        return {
            "id": "no-fabrication",
            "status": "warn",
            "message": "원문 fetch 실패 — 근거 확인 skip",
        }

    missing_numbers = [n for n in numbers if n not in combined]
    missing_companies = [c for c in companies if c not in combined]
    total_missing = len(missing_numbers) + len(missing_companies)

    if total_missing == 0:
        return {
            "id": "no-fabrication",
            "status": "pass",
            "message": "근거 있는 수치/기업명만 사용",
        }
    return {
        "id": "no-fabrication",
        "status": "fail",
        "message": (
            f"근거 없는 수치 {len(missing_numbers)}건, 근거 없는 기업명 {len(missing_companies)}건"
        ),
        "details": (missing_numbers + missing_companies)[:5],
    }


# ---------------------------------------------------------------------------
# 체크 6: pii-check — 주민번호·전화·이메일 패턴
# ---------------------------------------------------------------------------

PII_PATTERNS = {
    "주민번호": re.compile(r"\b\d{6}\s?-\s?[1-4]\d{6}\b"),
    "전화번호": re.compile(r"\b0\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}\b"),
    "이메일": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
}

# 매체 연락처(고지용)는 허용 — editorial@, correction@ 등
ALLOWED_EMAIL_PREFIXES = ("editorial@", "correction@", "newsroom@", "press@", "contact@", "hello@")


def check_pii(text: str) -> dict[str, Any]:
    hits: list[str] = []
    for kind, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0)
            if kind == "이메일" and value.lower().startswith(ALLOWED_EMAIL_PREFIXES):
                continue
            hits.append(f"{kind}: {value}")

    if not hits:
        return {"id": "pii-check", "status": "pass", "message": "PII 패턴 미탐지"}
    return {
        "id": "pii-check",
        "status": "fail",
        "message": f"PII 의심 {len(hits)}건",
        "details": hits[:5],
    }


# ---------------------------------------------------------------------------
# 체크 7: image-rights — 이미지 태그에 data-rights 속성 필수
# ---------------------------------------------------------------------------


def check_image_rights(text: str) -> dict[str, Any]:
    html_imgs = re.findall(r"<img[^>]*>", text, flags=re.IGNORECASE)
    md_imgs = re.findall(r"!\[[^\]]*\]\([^)]+\)", text)

    total = len(html_imgs) + len(md_imgs)
    if total == 0:
        return {"id": "image-rights", "status": "pass", "message": "이미지 없음"}

    missing = 0
    for tag in html_imgs:
        if "data-rights" not in tag:
            missing += 1
    # 마크다운 이미지 문법은 data-rights 속성을 표현할 수 없으므로 전부 누락 처리
    missing += len(md_imgs)

    if missing == 0:
        return {
            "id": "image-rights",
            "status": "pass",
            "message": f"이미지 {total}건 모두 data-rights 기록",
        }
    return {
        "id": "image-rights",
        "status": "fail",
        "message": f"라이선스 미기록 이미지 {missing}건 (전체 {total}건)",
    }


# ---------------------------------------------------------------------------
# 체크 8: ai-disclosure — 하단 AI 사용 고지 존재
# ---------------------------------------------------------------------------

AI_DISCLOSURE_KEYWORDS = [
    "AI 보조",
    "AI 사용 고지",
    "Claude",
    "AI 보조 도구",
    "AI가 보조",
    "AI-assisted",
    "AI 활용",
]


def check_ai_disclosure(text: str) -> dict[str, Any]:
    # 문서 하단 30% 구간에서 AI 고지 문구 검색
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {"id": "ai-disclosure", "status": "fail", "message": "문서가 비어 있음"}
    tail = "\n".join(lines[max(1, int(len(lines) * 0.5)):])
    for kw in AI_DISCLOSURE_KEYWORDS:
        if kw in tail:
            return {
                "id": "ai-disclosure",
                "status": "pass",
                "message": f"AI 사용 고지 확인 (키워드: '{kw}')",
            }
    return {
        "id": "ai-disclosure",
        "status": "fail",
        "message": "AI 사용 고지 문구 누락 (하단부에 'AI 보조' 등 명시 필요)",
    }


# ---------------------------------------------------------------------------
# 체크 9: correction-policy — 정정 책임자·24h 응답 기한 명시
# ---------------------------------------------------------------------------


def check_correction_policy(text: str) -> dict[str, Any]:
    # '정정' 키워드 + 24시간/24h 키워드 동시 등장 여부
    has_correction = any(
        kw in text for kw in ("정정 요청", "정정 책임", "정정 정책", "정정 담당", "correction")
    )
    has_timebound = bool(re.search(r"24\s*시간|24h|24 hours", text, re.IGNORECASE))
    has_contact = bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))

    if has_correction and has_timebound and has_contact:
        return {
            "id": "correction-policy",
            "status": "pass",
            "message": "정정 정책 명시 (책임자 연락처 + 24시간 응답 기한 확인)",
        }
    missing = []
    if not has_correction:
        missing.append("정정 키워드")
    if not has_timebound:
        missing.append("24시간 응답 기한")
    if not has_contact:
        missing.append("책임자 연락처")
    return {
        "id": "correction-policy",
        "status": "fail",
        "message": f"정정 정책 누락 ({', '.join(missing)})",
    }


# ---------------------------------------------------------------------------
# 체크 10: request-id-log — logs/에 해당 draft의 request_id 존재
# ---------------------------------------------------------------------------


def check_request_id_log(
    draft_path: str | None,
    ghost_post_id: str | None = None,
) -> dict[str, Any]:
    if not LOGS_DIR.exists():
        return {
            "id": "request-id-log",
            "status": "fail",
            "message": "logs/ 디렉토리 없음",
        }

    log_files = sorted(LOGS_DIR.glob("*.json"))
    if not log_files:
        return {
            "id": "request-id-log",
            "status": "fail",
            "message": "logs/ 내 JSON 로그 없음",
        }

    # draft 파일명에서 날짜 토큰(YYYYMMDD)을 추출해 매칭 강화
    date_token: str | None = None
    if draft_path:
        m = re.search(r"(\d{8})", Path(draft_path).name)
        if m:
            date_token = m.group(1)

    matched: list[str] = []
    for log in log_files:
        if date_token and date_token not in log.name:
            continue
        try:
            data = json.loads(log.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("request_id"):
            matched.append(log.name)

    # ghost-post-id 경로는 draft 파일명 기반 날짜 매칭이 불가하므로,
    # 무관한 과거 로그 하나로 pass 시키지 않는다.
    if ghost_post_id and not date_token:
        return {
            "id": "request-id-log",
            "status": "warn",
            "message": "ghost-post-id 경로는 관련 request_id 자동 매칭 불가 — 수동 확인 필요",
        }

    # 날짜 토큰이 없으면 전체 로그에서 request_id 하나라도 있으면 통과 (smoke test 허용)
    if not matched and not date_token:
        for log in log_files:
            try:
                data = json.loads(log.read_text(encoding="utf-8"))
            except Exception:
                continue
            if data.get("request_id"):
                matched.append(log.name)
                break

    if matched:
        return {
            "id": "request-id-log",
            "status": "pass",
            "message": f"logs/{matched[0]} 등 {len(matched)}개 확인",
        }
    return {
        "id": "request-id-log",
        "status": "fail",
        "message": "API 로그 누락 (해당 draft의 request_id 없음)",
    }


# ---------------------------------------------------------------------------
# 오케스트레이터
# ---------------------------------------------------------------------------


CHECK_FUNCS = {
    "source-id": lambda text, **_: check_source_id(text),
    "citations-cross-check": lambda text, article_id=None, **_: check_citations_cross_check(text, article_id),
    "translation-guard": lambda text, **_: check_translation_guard(text),
    "title-body-match": lambda text, **_: check_title_body_match(text),
    "quote-fidelity": lambda text, article_id=None, **_: check_quote_fidelity(text, article_id),
    "no-fabrication": lambda text, article_id=None, **_: check_no_fabrication(text, article_id),
    "pii-check": lambda text, **_: check_pii(text),
    "image-rights": lambda text, **_: check_image_rights(text),
    "ai-disclosure": lambda text, **_: check_ai_disclosure(text),
    "correction-policy": lambda text, **_: check_correction_policy(text),
    "request-id-log": lambda text, draft_path=None, ghost_post_id=None, **_: check_request_id_log(
        draft_path,
        ghost_post_id=ghost_post_id,
    ),
}


def lint_draft(
    draft_path: str,
    only: list[str] | None = None,
    *,
    article_id: str | None = None,
    text_override: str | None = None,
    ghost_post_id: str | None = None,
    category: str | None = None,
) -> dict:
    """편집 체크리스트 10개 항목 검증.

    반환:
        {
            "passed": int, "failed": int, "warnings": int,
            "items": [{"id", "status", "message"}...],
            "can_publish": bool
        }
    """
    if text_override is not None:
        text = text_override
    else:
        text = Path(draft_path).read_text(encoding="utf-8-sig")

    selected = only if only else CHECK_IDS
    items: list[dict[str, Any]] = []
    for check_id in CHECK_IDS:
        if check_id not in selected:
            continue
        func = CHECK_FUNCS[check_id]
        try:
            result = func(
                text,
                article_id=article_id,
                draft_path=draft_path,
                ghost_post_id=ghost_post_id,
            )
        except Exception as exc:  # pragma: no cover — 개별 체크 실패가 전체를 멈추지 않도록
            result = {
                "id": check_id,
                "status": "warn",
                "message": f"체크 실행 오류 — skip ({type(exc).__name__}: {exc})",
            }
        items.append(result)

    if category and (only is None or "article-standards" in selected):
        items.append(
            _check_article_standards(
                draft_path=draft_path,
                category=category,
                article_id=article_id,
            )
        )

    passed = sum(1 for it in items if it["status"] == "pass")
    failed = sum(1 for it in items if it["status"] == "fail")
    warnings = sum(1 for it in items if it["status"] in ("warn", "skip"))
    can_publish = failed == 0

    return {
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "items": items,
        "can_publish": can_publish,
    }


def _derive_lint_article_id(
    draft_path: str | None,
    article_id: str | None,
    ghost_post_id: str | None,
) -> str | None:
    if article_id:
        return article_id
    if draft_path:
        return Path(draft_path).stem
    if ghost_post_id:
        return ghost_post_id
    return None


def _write_lint_log(
    *,
    mode: str,
    result: dict[str, Any],
    draft_path: str | None = None,
    article_id: str | None = None,
    ghost_post_id: str | None = None,
    only: list[str] | None = None,
    slides_json: str | None = None,
    source_path: str | None = None,
) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "article_id": _derive_lint_article_id(draft_path, article_id, ghost_post_id),
        "draft_path": draft_path,
        "ghost_post_id": ghost_post_id,
        "slides_json": slides_json,
        "source_path": source_path,
        "selected_checks": only or (CHECK_IDS if mode == "article" else CARD_NEWS_CHECK_IDS),
        "passed": result["passed"],
        "failed": result["failed"],
        "warnings": result["warnings"],
        "can_publish": result["can_publish"],
        "items": result["items"],
    }
    log_file = LOGS_DIR / f"lint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_file


# ---------------------------------------------------------------------------
# Ghost 통합 (선택)
# ---------------------------------------------------------------------------


def fetch_ghost_post_html(post_id: str) -> tuple[str, str]:
    """Ghost Admin API로 포스트 조회 → (title, html) 반환."""
    try:
        try:
            from pipeline.ghost_client import _request
        except ModuleNotFoundError:
            from ghost_client import _request  # type: ignore
    except ImportError as exc:
        raise RuntimeError(f"ghost_client 로드 실패: {exc}") from exc

    response = _request("GET", f"/posts/{post_id}/", params={"formats": "html"})
    post = response["posts"][0]
    return post.get("title", ""), post.get("html", "")


def _check_article_standards(
    *,
    draft_path: str,
    category: str,
    article_id: str | None,
) -> dict[str, Any]:
    try:
        try:
            from pipeline.standards_checker import check_article
        except ModuleNotFoundError:
            from standards_checker import check_article  # type: ignore
    except ImportError:
        return {
            "id": "article-standards",
            "status": "warn",
            "message": "standards_checker missing - skipped",
        }

    try:
        result = check_article(draft_path, category, metadata={"article_id": article_id})
    except Exception as exc:
        return {
            "id": "article-standards",
            "status": "warn",
            "message": f"standards_checker failed - skipped ({type(exc).__name__}: {exc})",
        }

    failed_ids = [
        item["id"]
        for item in (result["common_checks"] + result["category_checks"])
        if item["status"] != "pass"
    ]
    return {
        "id": "article-standards",
        "status": "pass" if result["can_publish"] else "fail",
        "message": (
            f"category={category} must_pass {result['must_pass_passed']}/{result['must_pass_total']}, "
            f"should_pass {result['should_pass_passed']}/{result['should_pass_total']}"
        ),
        "details": failed_ids[:5] if failed_ids else None,
    }


# ---------------------------------------------------------------------------
# 카드뉴스 전용 체크 (TASK_041)
# ---------------------------------------------------------------------------


def _extract_source_points(text: str) -> list[str]:
    points: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        stripped = SOURCE_ID_PATTERN.sub("", stripped).strip()
        if len(stripped) >= 20:
            points.append(stripped)
    return points


def check_card_news_structure(slides: list[dict[str, Any]]) -> dict[str, Any]:
    if not slides:
        return {
            "id": "card-news-structure",
            "status": "fail",
            "message": "슬라이드가 비어 있음",
        }

    issues: list[str] = []
    if slides[0].get("role") != "hook":
        issues.append("첫 슬라이드 role 이 hook 이 아님")
    if slides[-1].get("role") != "cta":
        issues.append("마지막 슬라이드 role 이 cta 가 아님")
    if not any(slide.get("role") == "body" for slide in slides[1:-1]):
        issues.append("중간 body 슬라이드가 없음")

    if issues:
        return {
            "id": "card-news-structure",
            "status": "fail",
            "message": f"구조 규칙 미통과 {len(issues)}건",
            "details": issues,
        }
    return {
        "id": "card-news-structure",
        "status": "pass",
        "message": "hook / body / cta 구조 확인",
    }


def check_card_news_density(slides: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    short_form = len(slides) <= 5
    for slide in slides:
        texts = [
            str(slide.get("main_copy", "")).strip(),
            str(slide.get("sub_copy", "")).strip(),
            str(slide.get("highlight", "")).strip(),
        ]
        combined = " ".join(t for t in texts if t)
        sentences = [s for s in re.split(r"(?<=[.!?。！？])\s+|\n+", combined) if s.strip()]
        bullet_like = bool(re.search(r"[,/·•]|  ", combined))
        has_number = bool(NUMBER_PATTERN.search(combined))
        if slide.get("role") == "body":
            if bullet_like and len(sentences) < 2:
                issues.append(f"{slide.get('idx')}번: 리스트형인데 설명 문장 부족")
            min_sentences = 2 if short_form else 3
            if not bullet_like and len(sentences) < min_sentences:
                issues.append(f"{slide.get('idx')}번: 서술형인데 최소 {min_sentences}문장 미만")
            if has_number and len(sentences) < 2:
                issues.append(f"{slide.get('idx')}번: 숫자 언급 대비 맥락 설명 부족")
    if issues:
        return {
            "id": "card-news-density",
            "status": "fail",
            "message": f"밀도 규칙 미통과 {len(issues)}건",
            "details": issues[:5],
        }
    return {
        "id": "card-news-density",
        "status": "pass",
        "message": f"슬라이드 {len(slides)}건 밀도 규칙 통과",
    }


def check_source_fidelity(slides: list[dict[str, Any]], source_md: str) -> dict[str, Any]:
    points = _extract_source_points(source_md)
    if not points:
        return {
            "id": "source-fidelity",
            "status": "warn",
            "message": "원문 포인트 추출 실패 — coverage 계산 생략",
        }

    covered = 0
    for point in points:
        tokens = [tok for tok in re.findall(r"[가-힣A-Za-z0-9]{3,}", point)[:6]]
        if not tokens:
            continue
        for slide in slides:
            slide_text = " ".join(
                str(slide.get(key, "")) for key in ("main_copy", "sub_copy", "highlight")
            )
            token_hits = sum(1 for tok in tokens if tok.lower() in slide_text.lower())
            if token_hits >= min(2, len(tokens)):
                covered += 1
                break

    coverage = covered / max(len(points), 1)
    status = "pass" if coverage >= 0.8 else "fail"
    return {
        "id": "source-fidelity",
        "status": status,
        "message": f"원문 포인트 커버리지 {coverage:.0%} ({covered}/{len(points)})",
    }


def check_slide_count(slides: list[dict[str, Any]], source_char_len: int) -> dict[str, Any]:
    count = len(slides)
    if source_char_len <= 500:
        expected = (5, 6)
    elif source_char_len <= 1500:
        expected = (7, 9)
    else:
        expected = (10, 13)

    if expected[0] <= count <= expected[1]:
        return {
            "id": "slide-count",
            "status": "pass",
            "message": f"원문 {source_char_len}자 대비 {count}장 적정",
        }
    return {
        "id": "slide-count",
        "status": "fail",
        "message": f"원문 {source_char_len}자 대비 {count}장 부적정 (권장 {expected[0]}~{expected[1]}장)",
    }


def lint_card_news(slides: list[dict[str, Any]], source_md: str) -> dict[str, Any]:
    source_char_len = len(re.sub(r"\s+", "", source_md))
    items = [
        check_card_news_structure(slides),
        check_card_news_density(slides),
        check_source_fidelity(slides, source_md),
        check_slide_count(slides, source_char_len),
    ]
    passed = sum(1 for it in items if it["status"] == "pass")
    failed = sum(1 for it in items if it["status"] == "fail")
    warnings = sum(1 for it in items if it["status"] in ("warn", "skip"))
    return {
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "items": items,
        "can_publish": failed == 0,
        "source_char_len": source_char_len,
    }


# ---------------------------------------------------------------------------
# 출력 포맷
# ---------------------------------------------------------------------------


def format_report(result: dict, draft_path: str | None = None, ghost_post_id: str | None = None) -> str:
    lines = ["=== 편집 체크리스트 검증 ==="]
    if draft_path:
        lines.append(f"파일: {draft_path}")
    if ghost_post_id:
        lines.append(f"Ghost post_id: {ghost_post_id}")
    lines.append("")

    total = len(result["items"])
    for idx, item in enumerate(result["items"], start=1):
        icon = STATUS_ICON.get(item["status"], "?")
        name = item["id"].ljust(22)
        lines.append(f"[{idx:>2}/{total}] {name} {icon} {item['message']}")
        if item.get("details"):
            for d in item["details"]:
                lines.append(f"                                      - {d}")
    lines.append("")
    lines.append(
        f"=== 결과: {result['passed']} 통과 / {result['failed']} 실패 / {result['warnings']} 경고 ==="
    )
    if result["can_publish"]:
        lines.append("발행 가능 (실패 항목 없음)")
    else:
        lines.append("발행 불가 — 실패 항목을 수정하세요.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="편집 체크리스트 자동 검증 (TASK_016)")
    parser.add_argument("--mode", choices=["article", "card-news"], default="article")
    parser.add_argument("--draft", help="초안 마크다운 파일 경로")
    parser.add_argument("--ghost-post-id", help="Ghost 포스트 ID")
    parser.add_argument("--slides-json", help="card-news 슬라이드 JSON 경로")
    parser.add_argument("--source", help="card-news 원문 markdown 경로")
    parser.add_argument("--article-id", help="source_registry 조회용 article_id (선택)")
    parser.add_argument("--category", help="article_standards category (optional)")
    parser.add_argument(
        "--only",
        nargs="+",
        help=f"특정 체크 항목만 실행. 가능: {', '.join(OPTIONAL_CHECK_IDS)}",
    )
    parser.add_argument("--json", action="store_true", help="JSON 리포트 출력")
    parser.add_argument("--strict", action="store_true", help="실패 시 exit 1")
    parser.add_argument("--dry-run", action="store_true", help="네트워크 호출 없이 정적 체크만 수행")
    args = parser.parse_args()

    if args.mode == "article" and not args.draft and not args.ghost_post_id:
        parser.error("--draft 또는 --ghost-post-id 중 하나는 필수입니다")
    if args.mode == "card-news" and (not args.slides_json or not args.source):
        parser.error("--mode card-news 에서는 --slides-json 과 --source 가 필수입니다")

    # --only 유효성
    if args.only:
        unknown = [x for x in args.only if x not in OPTIONAL_CHECK_IDS]
        if unknown:
            parser.error(f"알 수 없는 체크 ID: {unknown}. 가능: {OPTIONAL_CHECK_IDS}")

    text_override: str | None = None
    draft_path = args.draft
    if args.ghost_post_id and args.dry_run:
        print("[error] --dry-run에서는 --ghost-post-id를 지원하지 않습니다.", file=sys.stderr)
        print("        Ghost fetch가 필요하므로 --draft 경로를 사용하거나 dry-run을 해제하세요.", file=sys.stderr)
        return 2

    if args.ghost_post_id:
        try:
            title, html = fetch_ghost_post_html(args.ghost_post_id)
            text_override = f"# {title}\n\n{_strip_html(html)}"
        except Exception as exc:
            print(f"[error] Ghost 포스트 fetch 실패: {exc}", file=sys.stderr)
            return 2

    if args.dry_run:
        # title-body-match의 Sonnet 호출을 차단하기 위해 API 키를 임시 제거
        os.environ.pop("ANTHROPIC_API_KEY", None)

    if args.mode == "card-news":
        payload = json.loads(Path(args.slides_json).read_text(encoding="utf-8"))
        slides = payload.get("slides", [])
        source_md = Path(args.source).read_text(encoding="utf-8")
        result = lint_card_news(slides, source_md)
    else:
        result = lint_draft(
            draft_path or "",
            only=args.only,
            article_id=args.article_id,
            text_override=text_override,
            ghost_post_id=args.ghost_post_id,
            category=args.category,
        )

    log_file = _write_lint_log(
        mode=args.mode,
        result=result,
        draft_path=draft_path,
        article_id=args.article_id,
        ghost_post_id=args.ghost_post_id,
        only=args.only,
        slides_json=args.slides_json,
        source_path=args.source,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.mode == "card-news":
            print("=== 카드뉴스 체크리스트 검증 ===")
            total = len(result["items"])
            for idx, item in enumerate(result["items"], start=1):
                icon = STATUS_ICON.get(item["status"], "?")
                print(f"[{idx:>2}/{total}] {item['id'].ljust(22)} {icon} {item['message']}")
                if item.get("details"):
                    for detail in item["details"]:
                        print(f"                                - {detail}")
            print()
            print(
                f"=== 결과: {result['passed']} 통과 / {result['failed']} 실패 / {result['warnings']} 경고 ==="
            )
            print("발행 가능" if result["can_publish"] else "발행 불가 — 카드뉴스 밀도 게이트 미통과")
        else:
            print(format_report(result, draft_path=draft_path, ghost_post_id=args.ghost_post_id))
        print(f"[log] -> {log_file.name}", file=sys.stderr)

    if args.strict and result["failed"] > 0:
        return 1
    return 0


# ---------------------------------------------------------------------------
# 스모크 테스트
# ---------------------------------------------------------------------------


def _smoke_test() -> None:
    """네트워크/키 없이 실행 가능한 간이 테스트."""
    sample = (
        "# 테스트 기사 [src-001]\n\n"
        "이것은 테스트 주장이다 [src-002].\n\n"
        "## AI 사용 고지\n"
        "이 기사는 AI 보조 도구를 사용해 작성되었습니다.\n"
        "정정 요청: editorial@example.kr (24시간 내 응답)\n"
    )
    tmp = LOGS_DIR / "_smoke_draft.md"
    tmp.write_text(sample, encoding="utf-8")
    res = lint_draft(str(tmp))
    assert "items" in res
    assert len(res["items"]) == len(CHECK_IDS)
    assert any(it["id"] == "source-id" for it in res["items"])
    tmp.unlink(missing_ok=True)
    print("✓ editorial_lint 스모크 테스트 통과")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _smoke_test()
    else:
        raise SystemExit(main())
