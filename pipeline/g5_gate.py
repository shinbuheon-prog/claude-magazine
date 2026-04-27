"""G5 cost overrun gate."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cost_tracking"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SLA_MINUTES = int(os.environ.get("G5_SLA_MINUTES", "30"))

try:
    from scripts import audit_budget
except ModuleNotFoundError:
    import audit_budget  # type: ignore


def _pending_path(article_id: str) -> Path:
    safe = str(article_id).replace("/", "-").replace("\\", "-")
    return DATA_DIR / f"g5_pending_{safe}.json"


def build_slack_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": f"G5 cost overrun: {result['article_id']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Current cost: ${result['current_cost_usd']:.2f} / ${result['budget_usd']:.2f} ({result['utilization_pct']:.1f}%)",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"SLA: {result['sla_deadline']}"},
            },
            {
                "type": "actions",
                "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Continue"}, "value": "continue"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Abort"}, "value": "abort"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Downgrade"}, "value": "downgrade"},
                ],
            },
        ],
    }


def notify_slack(result: dict[str, Any]) -> bool:
    webhook = os.environ.get("NOTIFY_SLACK_WEBHOOK")
    if not webhook:
        return False
    try:
        import requests
    except ImportError:
        return False
    try:
        requests.post(webhook, json=build_slack_payload(result), timeout=10)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[warn] Slack notify failed: {exc}", file=sys.stderr)
        return False


def check_and_notify(article_id: str) -> dict[str, Any]:
    result = audit_budget.check_article_budget(article_id)
    if not result["g5_triggered"]:
        result["action_required"] = None
        result["sla_deadline"] = None
        result["slack_notified"] = False
        return result

    result["action_required"] = "editor_decision"
    result["sla_deadline"] = (datetime.now(timezone.utc) + timedelta(minutes=SLA_MINUTES)).isoformat()
    result["slack_notified"] = notify_slack(result)
    pending = dict(result)
    pending["status"] = "pending"
    _pending_path(article_id).write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def apply_decision(article_id: str, decision: str) -> dict[str, Any]:
    normalized = "downgrade_to_haiku" if decision == "downgrade" else decision
    if normalized not in {"continue", "abort", "downgrade_to_haiku"}:
        raise ValueError(f"unsupported decision: {decision}")

    payload = audit_budget.read_article_cost(article_id)
    pending_path = _pending_path(article_id)
    original_budget = float(payload.get("original_estimated_budget_usd") or payload.get("estimated_budget_usd") or audit_budget.resolve_article_budget())
    approved_budget = original_budget
    if normalized == "continue":
        approved_budget = original_budget * 2.0
        status = "approved"
        model_override = None
    elif normalized == "abort":
        status = "killed"
        model_override = None
    else:
        status = "downgraded"
        model_override = "haiku"

    payload["original_estimated_budget_usd"] = original_budget
    payload["estimated_budget_usd"] = approved_budget
    payload["editor_decision"] = normalized
    payload["status"] = status
    if model_override:
        payload["model_override"] = model_override
    audit_budget.write_article_cost(article_id, payload)

    decision_payload = {
        "article_id": article_id,
        "decision": normalized,
        "status": status,
        "approved_budget_usd": approved_budget,
        "model_override": model_override,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    pending_path.write_text(json.dumps(decision_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return decision_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G5 cost overrun gate")
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--decide", choices=["continue", "abort", "downgrade"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="check without notifying Slack")
    args = parser.parse_args(argv)

    if bool(args.check) == bool(args.decide):
        parser.error("choose exactly one of --check or --decide")

    if args.check:
        if args.dry_run:
            old = os.environ.pop("NOTIFY_SLACK_WEBHOOK", None)
            try:
                result = check_and_notify(args.article_id)
            finally:
                if old is not None:
                    os.environ["NOTIFY_SLACK_WEBHOOK"] = old
        else:
            result = check_and_notify(args.article_id)
    else:
        result = apply_decision(args.article_id, args.decide or "")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
