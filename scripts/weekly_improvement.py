"""
Entry point for the weekly improvement loop.

Usage:
    python scripts/weekly_improvement.py
    python scripts/weekly_improvement.py --since-days 14
    python scripts/weekly_improvement.py --dry-run
    python scripts/weekly_improvement.py --output reports/custom.md
    python scripts/weekly_improvement.py --create-issue
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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
sys.path.insert(0, str(ROOT))

from pipeline.failure_collector import collect_failures  # noqa: E402
from pipeline import failure_repeat_detector  # noqa: E402
from pipeline.sop_updater import analyze_and_propose  # noqa: E402

REPORTS_DIR = ROOT / "reports"
LOGS_DIR = ROOT / "logs"
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _saturday_of(now: datetime | None = None) -> datetime:
    base = now or datetime.now(timezone.utc)
    delta = (base.weekday() - 5) % 7
    return (base - timedelta(days=delta)).replace(hour=0, minute=0, second=0, microsecond=0)


def default_report_path() -> Path:
    return REPORTS_DIR / f"improvement_{_saturday_of().strftime('%Y-%m-%d')}.md"


def _format_change_pp(value: float | None) -> str:
    if not isinstance(value, (int, float)):
        return "n/a"
    return f"{value * 100:+.1f}%p"


def load_priority_markers() -> list[dict[str, Any]]:
    queue_dir = getattr(failure_repeat_detector, "QUEUE_DIR")
    if not queue_dir.exists():
        return []
    markers: list[dict[str, Any]] = []
    for path in sorted(queue_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if payload.get("status") != "queued":
            continue
        payload["marker_path"] = str(path)
        markers.append(payload)
    return markers


def _render_summary(failures: dict[str, Any]) -> list[str]:
    lint = failures.get("editorial_lint_failures", [])
    corrections = failures.get("editor_corrections", [])
    anomalies = failures.get("langfuse_anomalies", [])
    standards = failures.get("standards_failures", [])

    lint_total = sum(item.get("count", 0) for item in lint)
    correction_total = sum(item.get("count", 0) for item in corrections)
    standards_total = sum(item.get("count", 0) for item in standards)

    def _top3(items: list[dict[str, Any]], key: str) -> str:
        if not items:
            return "none"
        return ", ".join(f"{item.get(key)} {item.get('count', 0)}x" for item in items[:3])

    lines = [
        "## Summary",
        "",
        f"- Period: {failures.get('period', {}).get('from', '')} ~ {failures.get('period', {}).get('to', '')}",
        f"- Published articles: {failures.get('total_articles', 0)}",
        f"- editorial_lint failures: {lint_total} ({_top3(lint, 'check_id')})",
        f"- standards failures: {standards_total} ({_top3(standards, 'rule_id')})",
        f"- editor corrections: {correction_total} ({_top3(corrections, 'type')})",
    ]
    if anomalies:
        lines.append(
            "- Langfuse anomalies: "
            + "; ".join(
                f"{item.get('metric')}: {item.get('baseline')} -> {item.get('current')} ({item.get('delta_pct')}%)"
                for item in anomalies
            )
        )
    else:
        lines.append("- Langfuse anomalies: none")
    lines.append("")

    cache_fact = ((failures.get("cache_signals") or {}).get("pipelines") or {}).get("fact_checker", {})
    citations = failures.get("citations_signals") or {}
    illustration = failures.get("illustration_signals") or {}
    publish = failures.get("publish_monthly_signals") or {}
    priority_markers = failures.get("repeat_failure_queue") or []

    lines.extend(
        [
            "## Operational Signals (TASK_053)",
            "",
            "### Cache",
            f"- fact_checker runs={cache_fact.get('runs', 0)} cache_enabled={cache_fact.get('cache_enabled_runs', 0)} "
            f"change_7d={_format_change_pp(cache_fact.get('hit_rate_change_7d'))} anomaly={cache_fact.get('anomaly', 'insufficient_data')}",
            "",
            "### Citations",
            f"- checks={citations.get('checks_total', 0)} by_status={citations.get('by_status', {})} "
            f"anomaly={citations.get('anomaly', 'insufficient_data')}",
            "",
            "### Illustration",
            f"- provider_distribution={illustration.get('provider_distribution', {})}",
            f"- fallback_rate={illustration.get('fallback_rate', 0)} budget_utilization={illustration.get('budget_utilization', 0)} "
            f"anomaly={illustration.get('anomaly', 'insufficient_data')}",
            "",
            "### Publish Monthly",
            f"- bottleneck_stage={publish.get('bottleneck_stage') or 'n/a'} "
            f"change={publish.get('stage_duration_change_7d', {})} "
            f"anomaly={publish.get('anomaly', 'insufficient_data')}",
            "",
        ]
    )
    if priority_markers:
        lines.extend(
            [
                "## Priority Queue (Repeated Failures)",
                "",
                f"- queued markers: {len(priority_markers)}",
            ]
        )
        for marker in priority_markers:
            for repeat in marker.get("repeats", []):
                lines.append(
                    f"- `{repeat.get('class')}` count={repeat.get('count')} "
                    f"stages={', '.join(repeat.get('stages') or []) or 'n/a'} "
                    f"window={marker.get('window_days')}d"
                )
        lines.append("")
    return lines


def _render_patterns(proposal: dict[str, Any]) -> list[str]:
    patterns = proposal.get("patterns", [])
    lines = [f"## Recurring Patterns ({len(patterns)})", ""]
    if not patterns:
        return lines + ["_No strong recurring pattern was detected._", ""]

    for index, pattern in enumerate(patterns, start=1):
        categories = ", ".join(pattern.get("affected_categories") or []) or "n/a"
        lines.append(
            f"### {index}. {pattern.get('pattern', '(unnamed)')} "
            f"(frequency={pattern.get('frequency', 0)}, categories={categories})"
        )
        if pattern.get("evidence"):
            lines.append(f"- Evidence: {pattern['evidence']}")
        lines.append("")
    return lines


def _render_updates(proposal: dict[str, Any]) -> list[str]:
    updates = proposal.get("proposed_updates", [])
    updates = sorted(updates, key=lambda item: PRIORITY_ORDER.get(str(item.get("priority") or "medium"), 1))
    lines = [f"## Proposed Updates ({len(updates)})", ""]
    if not updates:
        return lines + ["_No concrete update was proposed._", ""]

    for update in updates:
        target = update.get("target_file", "(unspecified)")
        priority = str(update.get("priority") or "medium").upper()
        lines.append(f"### [{priority}] {target}")
        if update.get("expected_impact"):
            lines.append(f"Expected impact: {update['expected_impact']}")
        if update.get("rationale"):
            lines.append(f"Rationale: {update['rationale']}")
        lines.append("")
        if update.get("diff"):
            lines.append("```diff")
            lines.append(str(update["diff"]).rstrip("\n"))
            lines.append("```")
        else:
            lines.append("_No diff attached. Manual drafting required._")
        lines.append("")
    return lines


def _render_checklist(proposal: dict[str, Any], failures: dict[str, Any]) -> list[str]:
    updates = proposal.get("proposed_updates", [])
    lines = ["## Review Checklist", ""]
    lines.append("1. Create a branch for the weekly improvement changes.")
    lines.append("2. Review suggested diffs and operational decisions.")
    lines.append("3. Run the smallest relevant tests locally.")
    lines.append('4. Commit with `chore: weekly SOP update` after human review.')
    lines.append("")

    if updates:
        lines.append("Suggested updates:")
        for update in updates:
            target = update.get("target_file", "(unspecified)")
            priority = str(update.get("priority") or "medium").upper()
            lines.append(f"- [ ] [{priority}] `{target}` reviewed")
    else:
        lines.append("- [ ] No code/doc diff proposed this week")
    lines.append("")
    lines.append("Operational follow-ups:")
    lines.append(
        f"- [ ] [OPERATIONS] cache anomaly `{((failures.get('cache_signals') or {}).get('pipelines') or {}).get('fact_checker', {}).get('anomaly', 'insufficient_data')}` reviewed"
    )
    lines.append(
        f"- [ ] [OPERATIONS] citations anomaly `{(failures.get('citations_signals') or {}).get('anomaly', 'insufficient_data')}` reviewed"
    )
    lines.append(
        f"- [ ] [OPERATIONS] illustration anomaly `{(failures.get('illustration_signals') or {}).get('anomaly', 'insufficient_data')}` reviewed"
    )
    lines.append(
        f"- [ ] [OPERATIONS] publish anomaly `{(failures.get('publish_monthly_signals') or {}).get('anomaly', 'insufficient_data')}` reviewed"
    )
    for marker in failures.get("repeat_failure_queue") or []:
        for repeat in marker.get("repeats", []):
            lines.append(
                f"- [ ] [PRIORITY] repeated failure `{repeat.get('class')}` ({repeat.get('count')}x) triaged"
            )
    lines.append("")
    return lines


def render_report(failures: dict[str, Any], proposal: dict[str, Any], period_label: str) -> str:
    lines: list[str] = [f"# Weekly Improvement Proposal - {period_label}", ""]
    lines.extend(_render_summary(failures))
    lines.extend(_render_patterns(proposal))
    lines.extend(_render_updates(proposal))
    lines.extend(_render_checklist(proposal, failures))

    lines.extend(
        [
            "## Meta",
            "",
            f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
            f"- Opus request_id: `{proposal.get('opus_request_id')}`" if proposal.get("opus_request_id") else "- Opus request_id: _n/a_",
            f"- confidence: {proposal.get('confidence')}" if proposal.get("confidence") is not None else "- confidence: n/a",
        ]
    )
    if proposal.get("notes"):
        lines.append(f"- notes: {proposal['notes']}")
    lines.extend(
        [
            "",
            "_This report is advisory only. Apply changes after human review._",
            "",
        ]
    )
    return "\n".join(lines)


def create_github_issue(report_path: Path, proposal: dict[str, Any]) -> str | None:
    try:
        subprocess.run(["gh", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[warn] gh CLI unavailable; skipping issue creation", file=sys.stderr)
        return None

    title = f"Weekly improvement proposal ({report_path.stem})"
    body = report_path.read_text(encoding="utf-8")
    try:
        completed = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        print(f"[warn] gh issue create failed: {exc.stderr}", file=sys.stderr)
        return None
    return completed.stdout.strip()


def notify_slack(proposal_count: int, report_path: Path) -> None:
    webhook = os.environ.get("NOTIFY_SLACK_WEBHOOK")
    if not webhook:
        return
    try:
        import requests

        requests.post(
            webhook,
            json={"text": f"weekly_improvement generated {proposal_count} proposals -> {report_path.name}"},
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[warn] Slack notify failed: {exc}", file=sys.stderr)


def run(since_days: int, output: Path, dry_run: bool, create_issue: bool) -> int:
    print(f"[info] collecting signals (since_days={since_days})", file=sys.stderr)
    failure_repeat_detector.REPORTS_DIR = REPORTS_DIR
    failure_repeat_detector.QUEUE_DIR = REPORTS_DIR / "auto_trigger_queue"
    failure_repeat_detector.ARCHIVE_DIR = failure_repeat_detector.QUEUE_DIR / "archived"
    failures = collect_failures(since_days=since_days)
    queued_markers = load_priority_markers()
    failures["repeat_failure_queue"] = queued_markers
    period = failures.get("period", {})
    period_label = f"{str(period.get('from', ''))[:10]} ~ {str(period.get('to', ''))[:10]}"

    if dry_run:
        proposal: dict[str, Any] = {
            "patterns": [],
            "proposed_updates": [],
            "opus_request_id": None,
            "confidence": 0.0,
            "notes": "dry-run: proposal generation skipped",
        }
    else:
        print("[info] generating proposal", file=sys.stderr)
        proposal = analyze_and_propose(failures)

    report_md = render_report(failures, proposal, period_label)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report_md, encoding="utf-8")
    output.with_suffix(".failures.json").write_text(
        json.dumps(failures, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    proposal_count = len(proposal.get("proposed_updates", []))
    print(f"[ok] report -> {output} (proposals={proposal_count}, dry_run={dry_run})", file=sys.stderr)

    notify_slack(proposal_count, output)
    if create_issue and not dry_run and proposal_count > 0:
        url = create_github_issue(output, proposal)
        if url:
            print(f"[ok] GitHub issue created: {url}", file=sys.stderr)
    if not dry_run:
        for marker in queued_markers:
            marker_path = marker.get("marker_path")
            if marker_path:
                failure_repeat_detector.acknowledge_marker(Path(marker_path))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the weekly improvement loop")
    parser.add_argument("--since-days", type=int, default=7, help="Look back N days")
    parser.add_argument("--output", help="Write the report to a specific path")
    parser.add_argument("--dry-run", action="store_true", help="Skip model analysis and render a dry-run report")
    parser.add_argument("--create-issue", action="store_true", help="Create a GitHub issue with gh CLI")
    args = parser.parse_args()

    output = Path(args.output) if args.output else default_report_path()
    return run(
        since_days=args.since_days,
        output=output,
        dry_run=args.dry_run,
        create_issue=args.create_issue,
    )


if __name__ == "__main__":
    raise SystemExit(main())
