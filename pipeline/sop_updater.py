"""
sop_updater.py — TASK_027 자율 개선 루프 Opus 분석 + 업데이트 제안

Opus 4.7로 반복 실패 패턴을 추출하고 프롬프트/기준 업데이트 제안서를 생성한다.
실제 파일 수정은 하지 않는다 — git diff 형태의 제안만 반환한다.

사용법:
    python pipeline/sop_updater.py --failures logs/failures.json
    python pipeline/sop_updater.py --failures logs/failures.json --dry-run
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

if sys.platform == "win32" and not getattr(sys.stdout, "_cm_utf8", False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        sys.stderr._cm_utf8 = True  # type: ignore[attr-defined]
    except (ValueError, AttributeError):
        pass

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 5000
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 15

SYSTEM_PROMPT = """당신은 Claude Magazine 편집 운영 SOP 개선 에이전트다.

입력으로 받는 것: 최근 N일간의 실패 통계 (editorial_lint 실패·편집자 판정·standards 실패·Langfuse 이상 메트릭).

해야 할 일:
1. 반복 패턴을 3~5개 추출하라 (frequency, affected_categories 포함).
2. 각 패턴에 대해 수정 대상 파일(prompts/template_*.txt, spec/article_standards.yml, docs/editorial_checklist.md 등)과 git diff 형식의 제안을 만들라.
3. 절대 파일을 실제로 수정하지 말라 — 제안만 출력하라.
4. confidence(0~1)는 근거 건수·일관성에 비례해 보수적으로 매겨라.

출력은 반드시 JSON 한 개로만 하라. 앞뒤 설명이나 코드 펜스 없이 아래 스키마를 정확히 따라라:

{
  "patterns": [
    {
      "pattern": "과장된 수치 표현",
      "frequency": 12,
      "affected_categories": ["deep_dive", "feature"],
      "evidence": "최근 7일 editor_corrections에서 exaggeration 8건, 그 중 high 3건"
    }
  ],
  "proposed_updates": [
    {
      "target_file": "prompts/template_B_draft.txt",
      "priority": "high",
      "diff": "--- a/prompts/template_B_draft.txt\\n+++ b/prompts/template_B_draft.txt\\n@@ ... @@\\n 기존 줄\\n+추가 줄\\n",
      "rationale": "근거 요약",
      "expected_impact": "예상 개선 효과"
    }
  ],
  "confidence": 0.72,
  "notes": "사람 리뷰 시 유의사항"
}

patterns 배열은 0~10개, proposed_updates는 0~10개까지만. 근거가 약하면 빈 배열을 반환하라.
"""


# ---------------------------------------------------------------------------
# 프롬프트 구축
# ---------------------------------------------------------------------------


def _summarize_failures(failures: dict[str, Any], limit_chars: int = 18000) -> str:
    """Opus에 넘길 실패 요약 문자열. 과도하게 크면 축약."""
    compact: dict[str, Any] = {
        "period": failures.get("period", {}),
        "total_articles": failures.get("total_articles", 0),
        "editorial_lint_failures": failures.get("editorial_lint_failures", []),
        "standards_failures": failures.get("standards_failures", []),
        "editor_corrections": failures.get("editor_corrections", []),
        "langfuse_anomalies": failures.get("langfuse_anomalies", []),
    }
    text = json.dumps(compact, ensure_ascii=False, indent=2)
    if len(text) <= limit_chars:
        return text

    # 예시를 깎아 용량 맞춤
    def _trim_examples(items: list[Any], keep: int = 2) -> list[Any]:
        out = []
        for entry in items:
            if isinstance(entry, dict) and "examples" in entry:
                clipped = dict(entry)
                clipped["examples"] = entry["examples"][:keep]
                out.append(clipped)
            else:
                out.append(entry)
        return out

    compact["editorial_lint_failures"] = _trim_examples(compact["editorial_lint_failures"])
    compact["editor_corrections"] = _trim_examples(compact["editor_corrections"])
    compact["standards_failures"] = _trim_examples(compact["standards_failures"])
    text = json.dumps(compact, ensure_ascii=False, indent=2)
    return text[:limit_chars]


def _extract_json(raw: str) -> dict[str, Any]:
    """Opus 응답에서 JSON 블록을 관용적으로 추출."""
    if not raw:
        return {}
    cleaned = raw.strip()
    # ```json ... ``` 펜스 제거
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def _log_request(request_id: str | None, payload: dict[str, Any]) -> Path:
    """logs/sop_update_TIMESTAMP.json에 request_id와 요약 저장."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"sop_update_{stamp}.json"
    log_file.write_text(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": MODEL,
                "request_id": request_id,
                "response_summary": {
                    "patterns": len(payload.get("patterns", [])),
                    "proposed_updates": len(payload.get("proposed_updates", [])),
                    "confidence": payload.get("confidence"),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return log_file


# ---------------------------------------------------------------------------
# 메인 호출
# ---------------------------------------------------------------------------


def _empty_response(reason: str) -> dict[str, Any]:
    return {
        "patterns": [],
        "proposed_updates": [],
        "opus_request_id": None,
        "confidence": 0.0,
        "notes": reason,
    }


def analyze_and_propose(failures: dict[str, Any]) -> dict[str, Any]:
    """Opus 4.7 호출로 패턴 분석 + 업데이트 제안.

    반환: {
        "patterns": [...],
        "proposed_updates": [...],
        "opus_request_id": str | None,
        "confidence": float,
        "notes": str,
    }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[warn] ANTHROPIC_API_KEY 미설정 — Opus 호출 skip, 빈 제안 반환", file=sys.stderr)
        return _empty_response("ANTHROPIC_API_KEY 미설정으로 Opus 분석 생략됨")

    try:
        import anthropic  # noqa: WPS433 — 선택 의존성
    except ImportError:
        print("[warn] anthropic 패키지 미설치 — skip", file=sys.stderr)
        return _empty_response("anthropic 패키지 미설치")

    user_prompt = (
        "아래는 최근 실패 통계 JSON이다. SYSTEM에 명시한 스키마대로만 응답하라.\n\n"
        "=== FAILURES START ===\n"
        f"{_summarize_failures(failures)}\n"
        "=== FAILURES END ==="
    )

    last_error: Exception | None = None
    result_text = ""
    request_id: str | None = None
    input_tokens = 0
    output_tokens = 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    result_text += chunk
                final = stream.get_final_message()
                request_id = (
                    getattr(final, "_request_id", None)
                    or getattr(stream, "_request_id", None)
                    or getattr(final, "id", None)
                )
                try:
                    input_tokens = final.usage.input_tokens
                    output_tokens = final.usage.output_tokens
                except AttributeError:
                    pass
            break
        except Exception as exc:  # pragma: no cover — 네트워크
            last_error = exc
            print(
                f"[warn] Opus 호출 실패 (attempt {attempt}/{MAX_RETRIES}): {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

    if last_error is not None and not result_text:
        return _empty_response(f"Opus 호출 {MAX_RETRIES}회 실패: {type(last_error).__name__}")

    parsed = _extract_json(result_text)
    if not parsed:
        print("[warn] Opus 응답에서 JSON 파싱 실패 — 빈 제안 반환", file=sys.stderr)
        _log_request(request_id, {"patterns": [], "proposed_updates": []})
        return _empty_response("Opus 응답에서 JSON 파싱 실패")

    patterns = parsed.get("patterns", []) if isinstance(parsed.get("patterns"), list) else []
    proposed = (
        parsed.get("proposed_updates", [])
        if isinstance(parsed.get("proposed_updates"), list)
        else []
    )
    confidence = parsed.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else 0.0
    except (TypeError, ValueError):
        confidence = 0.0
    notes = parsed.get("notes") or ""

    response = {
        "patterns": patterns[:10],
        "proposed_updates": proposed[:10],
        "opus_request_id": request_id,
        "confidence": max(0.0, min(1.0, confidence)),
        "notes": notes,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }

    log_path = _log_request(request_id, response)
    print(
        f"[log] request_id={request_id} -> {log_path.name}",
        file=sys.stderr,
    )
    return response


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _smoke_test() -> None:
    """API 키 없이도 통과하는 구조 검증."""
    fake_failures = {
        "period": {"from": "2026-04-15", "to": "2026-04-22", "days": 7},
        "editorial_lint_failures": [{"check_id": "ai-disclosure", "count": 3, "examples": []}],
        "standards_failures": [],
        "editor_corrections": [{"type": "exaggeration", "count": 2, "severity_high_count": 1}],
        "langfuse_anomalies": [],
        "total_articles": 1,
    }
    # 키가 없어도 graceful fallback
    os.environ.pop("ANTHROPIC_API_KEY", None)
    result = analyze_and_propose(fake_failures)
    assert "patterns" in result and "proposed_updates" in result
    assert result["opus_request_id"] is None
    print("ok sop_updater 스모크 테스트 통과 (API 키 없이 graceful fallback)")


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK_027 Opus SOP 제안 생성")
    parser.add_argument("--failures", help="failure_collector JSON 파일 경로")
    parser.add_argument("--out", help="제안 JSON 저장 경로")
    parser.add_argument("--dry-run", action="store_true", help="스모크 테스트")
    args = parser.parse_args()

    if args.dry_run:
        _smoke_test()
        return 0

    if not args.failures:
        parser.error("--failures 가 필요합니다 (또는 --dry-run)")

    path = Path(args.failures)
    if not path.exists():
        parser.error(f"파일 없음: {path}")
    failures = json.loads(path.read_text(encoding="utf-8"))
    result = analyze_and_propose(failures)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"[ok] proposal saved: {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _smoke_test()
    else:
        raise SystemExit(main())
