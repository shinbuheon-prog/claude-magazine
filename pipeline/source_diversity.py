"""
소스 다양성 규칙 엔진 (TASK_019)
모델: claude-haiku-4-5-20251001 (stance 분류)
사용법:
    python pipeline/source_diversity.py --article-id art-001
    python pipeline/source_diversity.py --sources src1.md src2.md --strict
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

try:
    from pipeline.source_registry import list_sources
except ModuleNotFoundError:
    from source_registry import list_sources  # type: ignore

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

RECENT_DAYS = 30
BACKGROUND_DAYS = 365
PUBLISHER_CONCENTRATION_LIMIT = 0.60

STANCE_VALUES = {"pro", "neutral", "con", "unknown"}


# ────────────────────────────────────────────────────────────────────────────
# Stance 분류 (Haiku 4.5)
# ────────────────────────────────────────────────────────────────────────────
def classify_stance(source_text: str, topic: str) -> str:
    """
    Haiku 4.5 호출 → pro | neutral | con | unknown 반환.
    ANTHROPIC_API_KEY 없거나 호출 실패 시 'unknown'을 반환한다 (예외 전파 금지).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return "unknown"
    if not (source_text or "").strip():
        return "unknown"

    try:
        from anthropic import Anthropic
    except ImportError:
        return "unknown"

    try:
        client = Anthropic(api_key=api_key)
        system_prompt = (
            "당신은 기술·정책 뉴스의 관점 분류기다.\n"
            "제공된 문서가 주어진 주제에 대해 찬성(pro), 중립(neutral), 반대(con) 중 어느 관점인지 한 단어로만 답하라.\n"
            "판단이 불가능하면 'unknown'을 출력하라.\n"
            "출력 형식: pro | neutral | con | unknown 중 하나의 소문자 단어. 다른 텍스트·설명 금지."
        )
        # 긴 원문 방지: 8000자로 잘라 전달
        preview = source_text[:8000]
        user_prompt = f"주제: {topic or '(미지정)'}\n\n--- 문서 ---\n{preview}"

        result_text = ""
        request_id = None
        with client.messages.stream(
            model=HAIKU_MODEL,
            max_tokens=16,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                result_text += chunk
            final = stream.get_final_message()
            request_id = getattr(final, "_request_id", None)

        _write_classify_log(topic, request_id, result_text)

        token = result_text.strip().lower().split()[0] if result_text.strip() else ""
        # 꼬리표 제거 (예: "pro.", "neutral,")
        token = token.strip(".,;:\"'`")
        if token in STANCE_VALUES:
            return token
        return "unknown"
    except Exception:
        return "unknown"


def _write_classify_log(topic: str, request_id: str | None, raw: str) -> None:
    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "model": HAIKU_MODEL,
            "topic": topic,
            "raw_response": (raw or "")[:256],
        }
        fname = LOGS_DIR / f"stance_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        fname.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # 로깅 실패는 조용히 무시 (분류 결과 자체를 깨뜨리지 않도록)
        return


# ────────────────────────────────────────────────────────────────────────────
# 파일 기반 소스 파서 (--sources 옵션 대비)
# ────────────────────────────────────────────────────────────────────────────
def _parse_source_file(path: Path) -> dict:
    """
    소스 파일 상단 YAML/front-matter 스타일 메타데이터를 느슨하게 파싱.
    예:
      ---
      url: https://example.com
      publisher: Example
      language: en
      stance: pro
      is_official: 1
      retrieved_at: 2026-04-10T00:00:00+00:00
      ---
      (본문)
    파일 메타가 없을 경우 경로에서 publisher만 추정하고 나머지는 기본값.
    """
    meta: dict = {
        "source_id": f"file:{path.name}",
        "url": str(path),
        "publisher": path.stem,
        "language": "unknown",
        "stance": "neutral",
        "is_official": 0,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return meta

    if text.startswith("---"):
        end_idx = text.find("\n---", 3)
        if end_idx > 0:
            header = text[3:end_idx].strip()
            for line in header.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    if key in {"url", "publisher", "language", "stance", "retrieved_at"}:
                        meta[key] = val
                    elif key == "is_official":
                        try:
                            meta["is_official"] = int(val)
                        except ValueError:
                            meta["is_official"] = 0
    return meta


# ────────────────────────────────────────────────────────────────────────────
# 4개 규칙
# ────────────────────────────────────────────────────────────────────────────
def _parse_retrieved_at(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _rule_language(sources: list[dict]) -> tuple[dict, list[str]]:
    ko_official = [s for s in sources if s.get("language") == "ko" and int(s.get("is_official") or 0) == 1]
    en_official = [s for s in sources if s.get("language") == "en" and int(s.get("is_official") or 0) == 1]
    recs: list[str] = []
    if not ko_official:
        recs.append("한국어 공식(정부·학술·기관) 출처 1개 이상 추가 필요")
    if not en_official:
        recs.append("영문 공식(정부·학술·기관) 출처 1개 이상 추가 필요")

    if ko_official and en_official:
        status = "pass"
        detail = (
            f"한국어 공식 {len(ko_official)}개 ("
            + ", ".join(sorted({s.get('publisher', '?') for s in ko_official}))
            + "), "
            + f"영문 공식 {len(en_official)}개 ("
            + ", ".join(sorted({s.get('publisher', '?') for s in en_official}))
            + ")"
        )
    else:
        status = "fail"
        missing_parts = []
        if not ko_official:
            missing_parts.append("한국어 공식 출처 없음")
        if not en_official:
            missing_parts.append("영문 공식 출처 없음")
        detail = " / ".join(missing_parts)
    return {"id": "language", "status": status, "detail": detail}, recs


def _rule_stance(sources: list[dict]) -> tuple[dict, list[str]]:
    counts = Counter((s.get("stance") or "unknown") for s in sources)
    categories = {k for k, v in counts.items() if v > 0 and k in {"pro", "neutral", "con"}}
    recs: list[str] = []

    breakdown = ", ".join(f"{k}: {counts.get(k, 0)}개" for k in ("pro", "neutral", "con", "unknown"))

    if len(categories) >= 2:
        status = "pass"
        detail = breakdown
    else:
        status = "fail"
        only = next(iter(categories), "unknown")
        detail = f"모든 소스가 동일 관점 ({only}) — {breakdown}"
        if "con" not in categories:
            recs.append("반대(con) 관점 소스 1개 이상 추가 권장")
        if "pro" not in categories and "neutral" not in categories:
            recs.append("중립/찬성 관점 소스 1개 이상 추가 권장")
    return {"id": "stance", "status": status, "detail": detail}, recs


def _rule_publisher(sources: list[dict]) -> tuple[dict, list[str]]:
    total = len(sources)
    recs: list[str] = []
    if total == 0:
        return {"id": "publisher", "status": "fail", "detail": "소스 0개"}, [
            "소스를 최소 2개 이상 확보해야 합니다."
        ]
    counts = Counter((s.get("publisher") or "?") for s in sources)
    top_pub, top_count = counts.most_common(1)[0]
    ratio = top_count / total
    detail = f"최대 집중: {top_pub} {ratio:.0%} ({top_count}/{total})"
    if ratio <= PUBLISHER_CONCENTRATION_LIMIT:
        status = "pass"
    else:
        status = "fail"
        detail = f"publisher '{top_pub}'가 전체 소스의 {ratio:.0%} 차지 ({top_count}/{total})"
        recs.append(f"'{top_pub}' 외 다른 발행처 출처를 추가해 집중도를 {int(PUBLISHER_CONCENTRATION_LIMIT*100)}% 이하로 낮추세요.")
    return {"id": "publisher", "status": status, "detail": detail}, recs


def _rule_recency(sources: list[dict]) -> tuple[dict, list[str]]:
    now = datetime.now(timezone.utc)
    recent = []
    background = []
    for s in sources:
        dt = _parse_retrieved_at(s.get("retrieved_at"))
        if dt is None:
            continue
        age = now - dt
        if age <= timedelta(days=RECENT_DAYS):
            recent.append(s)
        if age >= timedelta(days=BACKGROUND_DAYS):
            background.append(s)

    recs: list[str] = []
    if recent and background:
        status = "pass"
        detail = f"30일 이내: {len(recent)}개, 365일 초과(배경): {len(background)}개"
    else:
        status = "fail"
        parts = []
        if not recent:
            parts.append("30일 이내 소스 없음 — 시의성 부족")
            recs.append("최근 30일 이내 출처 1개 이상 추가 필요")
        if not background:
            parts.append("365일 초과 배경 소스 없음 — 맥락 부족")
            recs.append("1년 이상 된 배경 출처 1개 이상 추가 필요")
        detail = " / ".join(parts)
    return {"id": "recency", "status": status, "detail": detail}, recs


# ────────────────────────────────────────────────────────────────────────────
# 메인 엔진
# ────────────────────────────────────────────────────────────────────────────
def _check_sources(sources: list[dict]) -> dict:
    rules = []
    recommendations: list[str] = []

    for fn in (_rule_language, _rule_stance, _rule_publisher, _rule_recency):
        result, recs = fn(sources)
        rules.append(result)
        recommendations.extend(recs)

    failed = [r for r in rules if r["status"] != "pass"]
    passed = len(failed) == 0
    if passed:
        summary = "모든 규칙 통과"
    else:
        summary = f"{len(failed)}개 규칙 실패"

    # 중복 권고 제거 (순서 유지)
    seen: set[str] = set()
    unique_recs: list[str] = []
    for r in recommendations:
        if r not in seen:
            seen.add(r)
            unique_recs.append(r)

    return {
        "passed": passed,
        "rules": rules,
        "summary": summary,
        "recommendations": unique_recs,
    }


def check_diversity(article_id: str) -> dict:
    """
    source_registry에서 article_id 기준으로 소스 목록을 조회해 4개 규칙 검사.
    """
    sources = list_sources(article_id)
    return _check_sources(sources)


def check_diversity_from_files(paths: Iterable[str]) -> dict:
    sources = [_parse_source_file(Path(p)) for p in paths]
    return _check_sources(sources)


# ────────────────────────────────────────────────────────────────────────────
# 출력 포맷
# ────────────────────────────────────────────────────────────────────────────
_RULE_LABEL = {
    "language": "언어 다양성",
    "stance": "관점 다양성",
    "publisher": "발행처 집중도",
    "recency": "시효성",
}


def _format_report(result: dict, header: str, total: int) -> str:
    lines = ["=== 소스 다양성 검사 ===", header, f"총 소스: {total}개", ""]
    order = ["language", "stance", "publisher", "recency"]
    rule_map = {r["id"]: r for r in result["rules"]}
    for idx, rid in enumerate(order, start=1):
        r = rule_map.get(rid, {"status": "fail", "detail": "(미수행)"})
        icon = "✅" if r["status"] == "pass" else "⚠️ "
        label = _RULE_LABEL.get(rid, rid)
        lines.append(f"[{idx}/4] {label}")
        lines.append(f"  {icon} {r['detail']}")
        lines.append("")
    passed_count = sum(1 for r in result["rules"] if r["status"] == "pass")
    warn_count = len(result["rules"]) - passed_count
    lines.append(f"=== 결과: {passed_count} 통과 / {warn_count} 경고 ===")
    if result["recommendations"]:
        lines.append("권고:")
        for rec in result["recommendations"]:
            lines.append(f"  - {rec}")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="소스 다양성 규칙 엔진 (TASK_019)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--article-id", dest="article_id", help="source_registry 조회 기준 article_id")
    group.add_argument("--sources", nargs="+", help="소스 파일 경로 직접 지정")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="실패 시 exit 1 (기본은 경고만 출력하고 exit 0)",
    )
    parser.add_argument("--json", action="store_true", help="JSON 포맷으로 출력")
    parser.add_argument("--dry-run", action="store_true", help="검사 로직만 실행 (현재 구현에서는 영향 없음)")
    args = parser.parse_args()

    if args.article_id:
        sources = list_sources(args.article_id)
        header = f"article_id: {args.article_id}"
    else:
        sources = [_parse_source_file(Path(p)) for p in args.sources]
        header = f"sources: {len(args.sources)}개 파일"

    result = _check_sources(sources)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_report(result, header, len(sources)))

    if args.strict and not result["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
