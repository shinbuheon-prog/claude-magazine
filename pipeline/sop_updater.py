"""
Generate SOP update proposals from weekly failure signals.

Usage:
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

if (
    sys.platform == "win32"
    and "pytest" not in sys.modules
    and not getattr(sys.stdout, "_cm_utf8", False)
):
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

SYSTEM_PROMPT = """You are the Claude Magazine SOP improvement analyst.

Input is a weekly failure-and-operations summary JSON. Produce only JSON.

Rules:
1. Extract 3-5 recurring patterns when evidence is strong enough.
2. Propose updates as diffs or operational decisions.
3. Do not modify files directly. Suggest changes only.
4. Be conservative with confidence scores.
5. Treat cache, citations, illustration, and publish signals as operational inputs:
   - If they imply a prompt/spec/doc change, propose a normal file diff.
   - If they imply an operating policy decision, emit `target_file: "operations:<topic>"`.
   - If the signal is ambiguous, call out that human review is required.

Return this JSON schema only:
{
  "patterns": [
    {
      "pattern": "short description",
      "frequency": 3,
      "affected_categories": ["weekly_brief"],
      "evidence": "why this matters"
    }
  ],
  "proposed_updates": [
    {
      "target_file": "docs/editorial_checklist.md",
      "priority": "high",
      "diff": "--- a/file\\n+++ b/file\\n@@ ... @@\\n",
      "rationale": "why this change is suggested",
      "expected_impact": "expected effect"
    }
  ],
  "confidence": 0.72,
  "notes": "review notes"
}
"""


def _summarize_failures(failures: dict[str, Any], limit_chars: int = 18000) -> str:
    compact: dict[str, Any] = {
        "period": failures.get("period", {}),
        "total_articles": failures.get("total_articles", 0),
        "editorial_lint_failures": failures.get("editorial_lint_failures", []),
        "standards_failures": failures.get("standards_failures", []),
        "editor_corrections": failures.get("editor_corrections", []),
        "langfuse_anomalies": failures.get("langfuse_anomalies", []),
        "cache_signals": failures.get("cache_signals", {}),
        "citations_signals": failures.get("citations_signals", {}),
        "illustration_signals": failures.get("illustration_signals", {}),
        "publish_monthly_signals": failures.get("publish_monthly_signals", {}),
    }

    def _trim_examples(items: list[Any], keep: int = 2) -> list[Any]:
        trimmed = []
        for item in items:
            if isinstance(item, dict) and "examples" in item:
                clone = dict(item)
                clone["examples"] = list(item.get("examples", []))[:keep]
                trimmed.append(clone)
            else:
                trimmed.append(item)
        return trimmed

    compact["editorial_lint_failures"] = _trim_examples(compact["editorial_lint_failures"])
    compact["standards_failures"] = _trim_examples(compact["standards_failures"])
    compact["editor_corrections"] = _trim_examples(compact["editor_corrections"])

    if isinstance(compact["cache_signals"], dict):
        compact["cache_signals"] = {
            "pipelines": {
                name: {
                    "runs": details.get("runs", 0),
                    "cache_enabled_runs": details.get("cache_enabled_runs", 0),
                    "hit_rate_change_7d": details.get("hit_rate_change_7d"),
                    "anomaly": details.get("anomaly"),
                }
                for name, details in (compact["cache_signals"].get("pipelines") or {}).items()
            }
        }
    if isinstance(compact["citations_signals"], dict):
        compact["citations_signals"] = {
            "checks_total": compact["citations_signals"].get("checks_total", 0),
            "by_status": compact["citations_signals"].get("by_status", {}),
            "top_mismatched_article_ids": list(
                compact["citations_signals"].get("top_mismatched_article_ids", [])
            )[:5],
            "anomaly": compact["citations_signals"].get("anomaly"),
        }
    if isinstance(compact["illustration_signals"], dict):
        compact["illustration_signals"] = {
            "provider_distribution": compact["illustration_signals"].get("provider_distribution", {}),
            "fallback_rate": compact["illustration_signals"].get("fallback_rate"),
            "budget_utilization": compact["illustration_signals"].get("budget_utilization"),
            "fallback_reasons": compact["illustration_signals"].get("fallback_reasons", {}),
            "anomaly": compact["illustration_signals"].get("anomaly"),
        }
    if isinstance(compact["publish_monthly_signals"], dict):
        compact["publish_monthly_signals"] = {
            "recent_runs": list(compact["publish_monthly_signals"].get("recent_runs", []))[:3],
            "bottleneck_stage": compact["publish_monthly_signals"].get("bottleneck_stage"),
            "stage_duration_change_7d": compact["publish_monthly_signals"].get("stage_duration_change_7d", {}),
            "anomaly": compact["publish_monthly_signals"].get("anomaly"),
        }

    text = json.dumps(compact, ensure_ascii=False, indent=2)
    return text[:limit_chars]


def _extract_json(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned = raw.strip()
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
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"sop_update_{stamp}.json"
    log_path.write_text(
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
    return log_path


def _empty_response(reason: str) -> dict[str, Any]:
    return {
        "patterns": [],
        "proposed_updates": [],
        "opus_request_id": None,
        "confidence": 0.0,
        "notes": reason,
    }


def analyze_and_propose(failures: dict[str, Any]) -> dict[str, Any]:
    provider_kind = os.environ.get("CLAUDE_PROVIDER", "api").lower()
    if provider_kind == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("[warn] ANTHROPIC_API_KEY missing; returning empty proposal", file=sys.stderr)
        return _empty_response("ANTHROPIC_API_KEY missing")

    try:
        try:
            from pipeline.claude_provider import get_provider
        except ModuleNotFoundError:
            from claude_provider import get_provider  # type: ignore
    except ImportError:
        return _empty_response("claude_provider unavailable")

    user_prompt = (
        "Below is the weekly failure summary JSON. Follow the system schema strictly.\n\n"
        "=== FAILURES START ===\n"
        f"{_summarize_failures(failures)}\n"
        "=== FAILURES END ==="
    )

    request_id: str | None = None
    result_text = ""
    input_tokens = 0
    output_tokens = 0
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            provider = get_provider()
            result = provider.stream_complete(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                model_tier="sonnet",
                max_tokens=MAX_TOKENS,
            )
            request_id = result.request_id
            result_text = result.text
            input_tokens = result.input_tokens
            output_tokens = result.output_tokens
            break
        except Exception as exc:
            last_error = exc
            print(f"[warn] analysis call failed ({attempt}/{MAX_RETRIES}): {type(exc).__name__}: {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)

    if not result_text:
        return _empty_response(f"call failed: {type(last_error).__name__}" if last_error else "no response")

    parsed = _extract_json(result_text)
    if not parsed:
        _log_request(request_id, {"patterns": [], "proposed_updates": [], "confidence": 0.0})
        return _empty_response("response was not valid JSON")

    patterns = parsed.get("patterns") if isinstance(parsed.get("patterns"), list) else []
    proposed_updates = parsed.get("proposed_updates") if isinstance(parsed.get("proposed_updates"), list) else []
    try:
        confidence = float(parsed.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    payload = {
        "patterns": patterns[:10],
        "proposed_updates": proposed_updates[:10],
        "opus_request_id": request_id,
        "confidence": max(0.0, min(1.0, confidence)),
        "notes": parsed.get("notes") or "",
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    log_path = _log_request(request_id, payload)
    print(f"[log] request_id={request_id} -> {log_path.name}", file=sys.stderr)
    return payload


def _smoke_test() -> None:
    fake_failures = {
        "period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7},
        "total_articles": 2,
        "editorial_lint_failures": [{"check_id": "ai-disclosure", "count": 3, "examples": []}],
        "standards_failures": [],
        "editor_corrections": [{"type": "exaggeration", "count": 2, "severity_high_count": 1}],
        "langfuse_anomalies": [],
        "cache_signals": {"pipelines": {"fact_checker": {"runs": 4, "hit_rate_change_7d": -0.2, "anomaly": "degrading"}}},
        "citations_signals": {"checks_total": 4, "by_status": {"warn-mismatch": 2}, "anomaly": "mismatch_rising"},
        "illustration_signals": {"fallback_rate": 0.25, "anomaly": "fallback_rising"},
        "publish_monthly_signals": {"bottleneck_stage": "pdf_compile", "anomaly": "bottleneck_worsening"},
    }
    os.environ.pop("ANTHROPIC_API_KEY", None)
    result = analyze_and_propose(fake_failures)
    assert "patterns" in result and "proposed_updates" in result
    assert result["opus_request_id"] is None
    print("ok sop_updater smoke test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate weekly SOP proposals")
    parser.add_argument("--failures", help="Path to failure summary JSON")
    parser.add_argument("--out", help="Write proposal JSON to a file")
    parser.add_argument("--dry-run", action="store_true", help="Run smoke test")
    args = parser.parse_args()

    if args.dry_run:
        _smoke_test()
        return 0
    if not args.failures:
        parser.error("--failures is required unless --dry-run is used")

    payload = json.loads(Path(args.failures).read_text(encoding="utf-8"))
    result = analyze_and_propose(payload)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"[ok] proposal saved: {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _smoke_test()
    else:
        raise SystemExit(main())
