"""G2 automatic gate based on fact-check confirmed ratio."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
QUEUE_DIR = ROOT / "data" / "g2_queue"
QUEUE_DIR.mkdir(parents=True, exist_ok=True)
THRESHOLD_PASS = 0.85
THRESHOLD_REVISE = 0.50
SLA_HOURS = 2


def _log_path(article_id: str) -> Path:
    return LOGS_DIR / f"factcheck_{article_id}.json"


def _email_queue_path(article_key: str) -> Path:
    safe = str(article_key).replace("/", "-").replace("\\", "-")
    return QUEUE_DIR / f"g2_{safe}.json"


def _load_factcheck_summary(article_id: str | None = None, factcheck_log: str | None = None) -> tuple[str, dict[str, Any]]:
    if factcheck_log:
        path = Path(factcheck_log)
        article_key = article_id or path.stem.replace("factcheck_", "", 1)
    elif article_id:
        path = _log_path(article_id)
        article_key = article_id
    else:
        raise ValueError("article_id or factcheck_log is required")
    if not path.exists():
        raise FileNotFoundError(f"factcheck log not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    resolved_key = str(payload.get("article_id") or article_key or "unknown")
    return resolved_key, payload.get("verdict_summary") or {}


def build_slack_payload(result: dict[str, Any]) -> dict[str, Any]:
    decision = result["decision"]
    headline = "G2 review required" if decision == "g2_review" else "G2 publish block"
    return {
        "text": f"{headline}: {result['article_id']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Confirmed ratio: {result['confirmed_ratio']:.2%}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Recommendation: {result['recommendation']}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"SLA: {result['sla_deadline'] or 'immediate escalation'}",
                },
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


def queue_email_notification(result: dict[str, Any]) -> bool:
    notify_email = os.environ.get("NOTIFY_EMAIL", "").strip()
    if not notify_email:
        return False
    payload = {
        "article_id": result["article_id"],
        "to": notify_email,
        "decision": result["decision"],
        "confirmed_ratio": result["confirmed_ratio"],
        "recommendation": result["recommendation"],
        "sla_deadline": result["sla_deadline"],
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    queue_path = _email_queue_path(result["article_id"])
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


def evaluate(article_id: str | None = None, strict: bool = True, *, factcheck_log: str | None = None) -> dict[str, Any]:
    resolved_article_id, summary = _load_factcheck_summary(article_id, factcheck_log)
    confirmed_ratio = float(summary.get("confirmed_ratio") or 0.0)
    critical_issues = list(summary.get("critical_issues") or [])
    recommendation = str(summary.get("recommendation") or "revise")

    if confirmed_ratio >= THRESHOLD_PASS and not critical_issues:
        decision = "pass"
        sla_deadline = None
        escalation_required = False
    elif confirmed_ratio < THRESHOLD_REVISE:
        decision = "block"
        sla_deadline = None
        escalation_required = True
    else:
        decision = "g2_review"
        sla_deadline = (datetime.now(timezone.utc) + timedelta(hours=SLA_HOURS)).isoformat()
        escalation_required = bool(critical_issues)

    result = {
        "article_id": resolved_article_id,
        "confirmed_ratio": confirmed_ratio,
        "recommendation": recommendation,
        "decision": decision,
        "critical_issues": critical_issues,
        "sla_deadline": sla_deadline,
        "escalation_required": escalation_required or decision == "block",
        "slack_notified": False,
        "email_notified": False,
        "strict": strict,
    }
    if decision in {"g2_review", "block"}:
        result["slack_notified"] = notify_slack(result)
        result["email_notified"] = queue_email_notification(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G2 automatic gate")
    parser.add_argument("--article-id")
    parser.add_argument("--factcheck-log", help="fallback factcheck log path for legacy non-article-id runs")
    parser.add_argument("--strict", action="store_true", help="return non-zero for review or block")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="evaluate without notifications")
    args = parser.parse_args(argv)
    if not args.article_id and not args.factcheck_log:
        parser.error("either --article-id or --factcheck-log is required")

    if args.dry_run:
        old = os.environ.pop("NOTIFY_SLACK_WEBHOOK", None)
        old_email = os.environ.pop("NOTIFY_EMAIL", None)
        try:
            result = evaluate(args.article_id, args.strict, factcheck_log=args.factcheck_log)
        finally:
            if old is not None:
                os.environ["NOTIFY_SLACK_WEBHOOK"] = old
            if old_email is not None:
                os.environ["NOTIFY_EMAIL"] = old_email
    else:
        try:
            result = evaluate(args.article_id, args.strict, factcheck_log=args.factcheck_log)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
            print("[hint] pass --article-id from fact_checker or provide --factcheck-log for legacy runs", file=sys.stderr)
            return 2 if args.strict else 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== G2 Gate ===")
        print(f"  Article: {result['article_id']}")
        print(f"  Confirmed ratio: {result['confirmed_ratio']:.2%}")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Decision: {result['decision']}")
        if result.get("sla_deadline"):
            print(f"  G2 SLA: {result['sla_deadline']}")

    if args.strict:
        if result["decision"] == "pass":
            return 0
        if result["decision"] == "g2_review":
            return 1
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
