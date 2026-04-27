"""Comprehensive quality review using the publish-gate 13 criteria."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "template_quality_review.txt"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
COST_DIR = ROOT / "data" / "cost_tracking"
COST_DIR.mkdir(parents=True, exist_ok=True)
PASSING_SCORE = 4
MAGAZINE_SPECIFIC_IDS = {9, 10, 11, 12, 13}
QUALITY_REVIEW_OUTPUT_USD_PER_1K = 0.025
QUALITY_REVIEW_INPUT_USD_PER_1K = 0.005

try:
    from pipeline.claude_provider import get_provider
except ModuleNotFoundError:
    from claude_provider import get_provider  # type: ignore


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _load_prompt(draft_text: str, category: str | None, is_sponsored: bool) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8-sig")
    user_prompt = template.replace("{{article_draft_markdown}}", draft_text)
    trailer = "\n\nReturn valid JSON with keys: verdict, publishable, criteria_scores, priority_fixes, improved_body, decision."
    trailer += f"\ncategory={category or 'unknown'}\nis_sponsored={str(is_sponsored).lower()}"
    return user_prompt + trailer


def _extract_json_block(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    payload = json.loads(candidate)
    return payload if isinstance(payload, dict) else {}


def _normalize_criteria(criteria_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(criteria_scores, start=1):
        normalized.append(
            {
                "id": int(item.get("id", idx)),
                "criterion": str(item.get("criterion") or f"criterion_{idx}"),
                "score": int(item.get("score", 1)),
                "comment": str(item.get("comment") or ""),
                "fix_suggestion": item.get("fix_suggestion"),
            }
        )
    return normalized


def _derive_verdict(criteria_scores: list[dict[str, Any]]) -> tuple[str, bool, str]:
    passing = [item for item in criteria_scores if int(item.get("score", 0)) >= PASSING_SCORE]
    passed_ids = {int(item["id"]) for item in passing}
    if len(passed_ids) == 13:
        return "pass", True, "publish"
    if any(criteria_id not in passed_ids for criteria_id in MAGAZINE_SPECIFIC_IDS):
        return "fail", False, "rewrite"
    if len(passed_ids) >= 10:
        return "partial", False, "manual_review"
    return "fail", False, "rewrite"


def _write_log(article_id: str, payload: dict[str, Any]) -> Path:
    path = LOGS_DIR / f"quality_review_{article_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _monthly_cost_path(month: str) -> Path:
    return COST_DIR / f"quality_review_cost_{month}.json"


def _estimate_cost(total_tokens: int) -> float:
    input_tokens = int(total_tokens * 0.67)
    output_tokens = max(0, total_tokens - input_tokens)
    return (input_tokens / 1000.0) * QUALITY_REVIEW_INPUT_USD_PER_1K + (output_tokens / 1000.0) * QUALITY_REVIEW_OUTPUT_USD_PER_1K


def _read_quality_review_cost(month: str) -> dict[str, Any]:
    path = _monthly_cost_path(month)
    if not path.exists():
        return {"month": month, "total_usd": 0.0, "articles": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"month": month, "total_usd": 0.0, "articles": {}}
    payload.setdefault("month", month)
    payload.setdefault("total_usd", 0.0)
    payload.setdefault("articles", {})
    return payload


def _record_quality_review_cost(article_id: str, total_tokens: int) -> dict[str, Any]:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    cap = max(0.0, float(os.environ.get("QUALITY_REVIEW_MONTHLY_USD_CAP", "0.0") or 0.0))
    payload = _read_quality_review_cost(month)
    estimated_cost = _estimate_cost(total_tokens)
    previous_cost = float((payload.get("articles") or {}).get(article_id, 0.0) or 0.0)
    new_total = max(0.0, float(payload.get("total_usd") or 0.0) - previous_cost + estimated_cost)
    payload["articles"][article_id] = estimated_cost
    payload["total_usd"] = new_total
    cost_path = _monthly_cost_path(month)
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    cost_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "month": month,
        "article_cost_usd": estimated_cost,
        "monthly_total_usd": new_total,
        "cap_usd": cap,
        "cap_exceeded": cap > 0 and new_total > cap,
    }


def _preview_quality_review_cost(total_tokens: int) -> dict[str, Any]:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    cap = max(0.0, float(os.environ.get("QUALITY_REVIEW_MONTHLY_USD_CAP", "0.0") or 0.0))
    payload = _read_quality_review_cost(month)
    estimated_cost = _estimate_cost(total_tokens)
    projected_total = max(0.0, float(payload.get("total_usd") or 0.0) + estimated_cost)
    return {
        "month": month,
        "article_cost_usd": estimated_cost,
        "monthly_total_usd": projected_total,
        "cap_usd": cap,
        "cap_exceeded": cap > 0 and projected_total > cap,
    }


def _apply_sponsored_checks(draft_text: str, criteria_scores: list[dict[str, Any]], priority_fixes: list[dict[str, Any]]) -> None:
    lowered = draft_text.lower()
    has_ad_label = "sponsored" in lowered or "advertisement" in lowered or "ad " in lowered
    if not has_ad_label:
        for item in criteria_scores:
            if item["id"] == 12:
                item["score"] = min(int(item.get("score", 1)), 1)
                item["comment"] = "Sponsored label or footer not found in draft."
                item["fix_suggestion"] = "Add a clear Sponsored Content or AD disclosure."
                priority_fixes.append(
                    {
                        "location": "draft footer",
                        "problem": "Sponsored label/footer missing",
                        "recommended_fix": "Insert Sponsored Content labeling and disclosure footer.",
                    }
                )
                break


def _enforce_verdict(criteria_scores: list[dict[str, Any]], draft_text: str, *, is_sponsored: bool) -> tuple[str, bool, str, list[dict[str, Any]]]:
    fixes: list[dict[str, Any]] = []
    if is_sponsored:
        _apply_sponsored_checks(draft_text, criteria_scores, fixes)
    verdict, publishable, decision = _derive_verdict(criteria_scores)
    return verdict, publishable, decision, fixes


def review_draft(
    draft_path: str,
    article_id: str,
    category: str | None = None,
    is_sponsored: bool = False,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    draft_text = Path(draft_path).read_text(encoding="utf-8-sig")
    prompt = _load_prompt(draft_text, category, is_sponsored)
    total_tokens = _estimate_tokens(prompt)
    if dry_run:
        cost_status = _preview_quality_review_cost(total_tokens)
        return {
            "article_id": article_id,
            "draft_path": draft_path,
            "verdict": "partial",
            "publishable": False,
            "criteria_scores": [],
            "priority_fixes": [],
            "improved_body": "",
            "decision": "manual_review",
            "request_id": None,
            "total_tokens": total_tokens,
            "cost_status": cost_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    provider = get_provider()
    result = provider.stream_complete(
        system="You are the editor-in-chief quality reviewer. Return strict JSON only.",
        user=prompt,
        model_tier="opus",
        max_tokens=8000,
    )
    payload = _extract_json_block(result.text)
    criteria_scores = _normalize_criteria(list(payload.get("criteria_scores") or []))
    verdict, publishable, decision, enforced_fixes = _enforce_verdict(criteria_scores, draft_text, is_sponsored=is_sponsored)
    priority_fixes = list(payload.get("priority_fixes") or [])
    priority_fixes.extend(enforced_fixes)
    cost_status = _record_quality_review_cost(article_id, result.input_tokens + result.output_tokens or total_tokens)
    if cost_status["cap_exceeded"]:
        verdict = "fail"
        publishable = False
        decision = "rewrite"
        priority_fixes.append(
            {
                "location": "quality_review budget",
                "problem": "Monthly quality review budget exceeded",
                "recommended_fix": "Pause additional Opus quality reviews or raise the approved cap.",
            }
        )

    review = {
        "article_id": article_id,
        "draft_path": draft_path,
        "verdict": verdict,
        "publishable": publishable,
        "criteria_scores": criteria_scores,
        "priority_fixes": priority_fixes,
        "improved_body": str(payload.get("improved_body") or ""),
        "decision": decision,
        "request_id": result.request_id,
        "total_tokens": result.input_tokens + result.output_tokens or total_tokens,
        "cost_status": cost_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _write_log(article_id, review)
    return review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Comprehensive quality review")
    parser.add_argument("--draft", required=True)
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--category")
    parser.add_argument("--sponsored", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="fail returns exit 1")
    parser.add_argument("--dry-run", action="store_true", help="estimate only, no model call")
    args = parser.parse_args(argv)

    result = review_draft(
        args.draft,
        args.article_id,
        category=args.category,
        is_sponsored=args.sponsored,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Quality Review ===")
        print(f"  Article: {result['article_id']}")
        print(f"  Verdict: {result['verdict']}")
        print(f"  Publishable: {result['publishable']}")
        print(f"  Decision: {result['decision']}")
        if result["priority_fixes"]:
            print(f"  Priority fixes: {len(result['priority_fixes'])}")

    if args.strict and result["verdict"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
