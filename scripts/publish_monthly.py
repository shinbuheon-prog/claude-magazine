"""
Monthly publish orchestrator.

Supports checkpointed execution with small operational UX helpers:
- --status
- --reset-stage
- --from-stage
- telemetry persisted in reports/publish_state_<month>.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if sys.platform == "win32" and not getattr(sys.stdout, "_utf8_wrapped", False):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout._utf8_wrapped = True  # type: ignore[attr-defined]
        except Exception:
            pass

try:
    import yaml  # type: ignore
except ImportError:
    print("PyYAML is required.", file=sys.stderr)
    sys.exit(1)

try:
    from pipeline.failure_playbook import generate_failure_report
except ModuleNotFoundError:
    from failure_playbook import generate_failure_report  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "drafts" / "issues"
REPORTS_DIR = ROOT / "reports"
LOGS_DIR = ROOT / "logs"

STAGE_ORDER = [
    "plan_loaded",
    "quality_gate",
    "disclosure_injected",
    "pdf_compile",
    "ghost_publish",
    "newsletter",
    "sns",
]
STAGE_LABELS = {
    "plan_loaded": "Plan Loaded",
    "quality_gate": "Quality Gate",
    "disclosure_injected": "Disclosure",
    "pdf_compile": "PDF Compile",
    "ghost_publish": "Ghost Publish",
    "newsletter": "Newsletter",
    "sns": "SNS",
}
STAGE_STATE_KEYS = {
    "plan_loaded": "plan_loaded",
    "quality_gate": "quality_gate",
    "disclosure_injected": "disclosure_injected",
    "pdf_compile": "pdf_compiled",
    "ghost_publish": "ghost_published",
    "newsletter": "newsletter_sent",
    "sns": "sns_distributed",
}
STATE_ALIASES = {
    "pdf_compile": ["pdf_compile", "pdf_compiled"],
    "ghost_publish": ["ghost_publish", "ghost_published"],
    "newsletter": ["newsletter", "newsletter_sent"],
    "sns": ["sns", "sns_distributed"],
    "disclosure_injected": ["disclosure", "disclosure_injected"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(month: str) -> Path:
    return REPORTS_DIR / f"publish_state_{month}.json"


def _normalize_state(state: dict[str, Any], month: str) -> dict[str, Any]:
    normalized = {
        "month": state.get("month") or month,
        "stages": dict(state.get("stages") or {}),
        "telemetry": dict(state.get("telemetry") or {}),
        "errors": dict(state.get("errors") or {}),
        "last_updated": state.get("last_updated"),
    }
    stages = normalized["stages"]
    for stage, aliases in STATE_ALIASES.items():
        target_key = STAGE_STATE_KEYS[stage]
        if target_key in stages:
            continue
        for alias in aliases:
            if alias in stages:
                stages[target_key] = stages[alias]
                break
    return normalized


def _load_state(month: str) -> dict[str, Any]:
    path = _state_path(month)
    if not path.exists():
        return {"month": month, "stages": {}, "telemetry": {}, "last_updated": None}
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    return _normalize_state(payload, month)


def _save_state(month: str, state: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = _utc_now()
    with _state_path(month).open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _record_telemetry(state: dict[str, Any], stage: str, started_at: str, finished_at: str, cost_usd: float | None = None) -> None:
    started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    finished_dt = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    state.setdefault("telemetry", {})[stage] = {
        "started": started_at,
        "finished": finished_at,
        "duration_sec": round(max(0.0, (finished_dt - started_dt).total_seconds()), 3),
        "cost_usd": cost_usd,
    }


def load_plan(month: str) -> dict[str, Any]:
    path = ISSUES_DIR / f"{month}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Plan not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _validate_stage_name(name: str) -> str:
    if name in STAGE_ORDER:
        return name
    match = difflib.get_close_matches(name, STAGE_ORDER, n=1)
    if match:
        raise ValueError(f"Unknown stage '{name}'. Did you mean '{match[0]}'?")
    raise ValueError(f"Unknown stage '{name}'. Expected one of: {', '.join(STAGE_ORDER)}")


def _confirm_or_exit(question: str, yes: bool) -> None:
    if yes:
        return
    answer = input(f"{question} [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        raise SystemExit(1)


def _estimate_stage_cost(stage: str) -> float | None:
    prefixes = {
        "quality_gate": ("lint_", "factcheck_", "standards_"),
        "ghost_publish": ("publish_",),
    }.get(stage)
    if not prefixes or not LOGS_DIR.exists():
        return None
    total = 0.0
    found = False
    for path in LOGS_DIR.glob("*.json"):
        if not path.name.startswith(prefixes):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        cost = payload.get("cost_usd")
        if cost is None:
            continue
        found = True
        total += float(cost)
    return round(total, 6) if found else None


def _status_line(stage: str, state: dict[str, Any], index: int) -> str:
    key = STAGE_STATE_KEYS[stage]
    value = state.get("stages", {}).get(key)
    icon = "done" if value else "todo"
    summary = ""
    if stage == "plan_loaded" and value:
        summary = f"articles={state['stages'].get('article_count', 0)}"
    elif stage == "quality_gate" and isinstance(value, dict):
        summary = f"passed={value.get('passed', 0)} failed={value.get('failed', 0)}"
    elif isinstance(value, list):
        summary = f"items={len(value)}"
    elif isinstance(value, dict):
        summary = "completed"
    elif isinstance(value, str):
        summary = value
    elif value is True:
        summary = "completed"
    return f"[{index}/{len(STAGE_ORDER)}] {stage:<20} {icon:<4} {summary}".rstrip()


def print_status(month: str, state: dict[str, Any], strict: bool) -> int:
    print(f"=== Monthly Publish Status: {month} ===")
    for index, stage in enumerate(STAGE_ORDER, start=1):
        print(_status_line(stage, state, index))
    print(f"last_updated: {state.get('last_updated') or 'n/a'}")
    if strict and any(not state.get("stages", {}).get(STAGE_STATE_KEYS[stage]) for stage in STAGE_ORDER):
        return 1
    return 0


def reset_stage(month: str, state: dict[str, Any], stage: str) -> int:
    key = STAGE_STATE_KEYS[stage]
    state.get("stages", {}).pop(key, None)
    state.get("telemetry", {}).pop(stage, None)
    state.get("errors", {}).pop(stage, None)
    _save_state(month, state)
    print(f"Reset stage: {stage}")
    return 0


def _set_stage_error(state: dict[str, Any], stage: str, message: str) -> None:
    state.setdefault("errors", {})[stage] = message


def _clear_stage_error(state: dict[str, Any], stage: str) -> None:
    state.setdefault("errors", {}).pop(stage, None)


def _write_failure_playbook(month: str, stage: str, error_output: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"failure_{month}_{stage}.md"
    path.write_text(
        generate_failure_report(month, stage, error_output, _state_path(month)),
        encoding="utf-8",
    )
    return path


def _stage_start_message(stage: str, index: int) -> str:
    return f"[{index}/{len(STAGE_ORDER)}] {STAGE_LABELS[stage]}"


def stage_plan_loaded(args, state, plan) -> bool | None:
    if state["stages"].get("plan_loaded"):
        print(f"{_stage_start_message('plan_loaded', 1)} already completed")
        _clear_stage_error(state, "plan_loaded")
        return True
    total = len(plan.get("articles", []))
    print(f"{_stage_start_message('plan_loaded', 1)}: {plan.get('issue')} ({total} articles)")
    state["stages"]["plan_loaded"] = True
    state["stages"]["article_count"] = total
    _clear_stage_error(state, "plan_loaded")
    return True


def stage_quality_gate(args, state, plan) -> bool | None:
    if state["stages"].get("quality_gate", {}).get("passed") is not None:
        print(f"{_stage_start_message('quality_gate', 2)} already completed")
        _clear_stage_error(state, "quality_gate")
        return True
    articles = plan.get("articles", [])
    passed, failed, errors = 0, 0, []
    print(f"{_stage_start_message('quality_gate', 2)}")
    for article in articles:
        status = article.get("status")
        if status in {"approved", "published", "lint"}:
            passed += 1
        else:
            failed += 1
            errors.append(f"{article.get('slug')}: status={status}")
    state["stages"]["quality_gate"] = {"passed": passed, "failed": failed, "errors": errors[:10]}
    print(f"passed={passed} failed={failed}")
    if failed > 0 and not args.force:
        _set_stage_error(state, "quality_gate", "\n".join(errors[:10]) or "Quality gate failed")
        print("Quality gate failed. Use --force to continue.", file=sys.stderr)
        return False
    _clear_stage_error(state, "quality_gate")
    return True


def stage_disclosure(args, state, plan) -> bool | None:
    if state["stages"].get("disclosure_injected"):
        print(f"{_stage_start_message('disclosure_injected', 3)} already completed")
        _clear_stage_error(state, "disclosure_injected")
        return True
    print(f"{_stage_start_message('disclosure_injected', 3)}")
    if args.dry_run:
        print("(dry-run) disclosure injection skipped")
    state["stages"]["disclosure_injected"] = True
    _clear_stage_error(state, "disclosure_injected")
    return True


def stage_pdf_compile(args, state, plan) -> bool | None:
    if args.skip_pdf:
        print(f"{_stage_start_message('pdf_compile', 4)} skipped (--skip-pdf)")
        return None
    if state["stages"].get("pdf_compiled"):
        print(f"{_stage_start_message('pdf_compile', 4)} already completed")
        _clear_stage_error(state, "pdf_compile")
        return True
    print(f"{_stage_start_message('pdf_compile', 4)}")
    cmd = ["python", str(ROOT / "scripts" / "compile_monthly_pdf.py"), "--month", args.month]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.force:
        cmd.append("--force")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        _set_stage_error(state, "pdf_compile", str(exc))
        print(f"PDF compile failed: {exc}", file=sys.stderr)
        return False
    pdf_path = ROOT / "output" / f"claude-magazine-{args.month}.pdf"
    state["stages"]["pdf_compiled"] = str(pdf_path) if pdf_path.exists() and not args.dry_run else True
    _clear_stage_error(state, "pdf_compile")
    return True


def stage_ghost_publish(args, state, plan) -> bool | None:
    if not args.publish:
        print(f"{_stage_start_message('ghost_publish', 5)} skipped (--publish not set)")
        return None
    if state["stages"].get("ghost_published"):
        print(f"{_stage_start_message('ghost_publish', 5)} already completed")
        _clear_stage_error(state, "ghost_publish")
        return True
    print(f"{_stage_start_message('ghost_publish', 5)}")
    if args.dry_run:
        print("(dry-run) ghost publish skipped")
        return None
    if not args.confirm:
        _set_stage_error(state, "ghost_publish", "--confirm is required with --publish")
        print("--confirm is required with --publish", file=sys.stderr)
        return False
    published_ids = [a.get("slug") for a in plan.get("articles", []) if a.get("status") == "approved"]
    state["stages"]["ghost_published"] = published_ids
    _clear_stage_error(state, "ghost_publish")
    return True


def stage_newsletter(args, state, plan) -> bool | None:
    if not args.publish:
        print(f"{_stage_start_message('newsletter', 6)} skipped (--publish not set)")
        return None
    if state["stages"].get("newsletter_sent"):
        print(f"{_stage_start_message('newsletter', 6)} already completed")
        _clear_stage_error(state, "newsletter")
        return True
    print(f"{_stage_start_message('newsletter', 6)}")
    if args.dry_run:
        print("(dry-run) newsletter skipped")
        return None
    state["stages"]["newsletter_sent"] = True
    _clear_stage_error(state, "newsletter")
    return True


def stage_sns(args, state, plan) -> bool | None:
    if args.skip_sns:
        print(f"{_stage_start_message('sns', 7)} skipped (--skip-sns)")
        return None
    if state["stages"].get("sns_distributed"):
        print(f"{_stage_start_message('sns', 7)} already completed")
        _clear_stage_error(state, "sns")
        return True
    print(f"{_stage_start_message('sns', 7)}")
    if args.dry_run:
        print("(dry-run) sns distribution skipped")
        return None
    distributed = {
        article.get("slug"): ["sns", "linkedin", "twitter", "instagram"]
        for article in plan.get("articles", [])
        if article.get("status") in {"approved", "published"}
    }
    state["stages"]["sns_distributed"] = distributed
    _clear_stage_error(state, "sns")
    return True


def write_report(month: str, state: dict[str, Any], plan: dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"publish_{month}.md"
    lines = [
        f"# Monthly Publish Report: {month}",
        "",
        f"- Issue: {plan.get('issue')}",
        f"- Theme: {plan.get('theme')}",
        f"- Editor in chief: {plan.get('editor_in_chief')}",
        f"- Generated at: {_utc_now()}",
        "",
        "## Stages",
        "",
    ]
    for stage in STAGE_ORDER:
        key = STAGE_STATE_KEYS[stage]
        value = state["stages"].get(key)
        icon = "done" if value else "todo"
        telemetry = state.get("telemetry", {}).get(stage) or {}
        duration = telemetry.get("duration_sec")
        duration_text = f" ({duration}s)" if duration is not None else ""
        lines.append(f"- {icon} {STAGE_LABELS[stage]}{duration_text}")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _run_stage(stage_name: str, stage_fn: Callable[..., bool | None], args, state, plan) -> bool | None:
    started_at = _utc_now()
    ok = stage_fn(args, state, plan)
    finished_at = _utc_now()
    if ok is True:
        _record_telemetry(state, stage_name, started_at, finished_at, _estimate_stage_cost(stage_name))
    elif ok is None:
        state.setdefault("telemetry", {}).pop(stage_name, None)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Monthly publish orchestrator")
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument("--skip-sns", action="store_true")
    parser.add_argument("--status", action="store_true", help="Show publish status and exit")
    parser.add_argument("--strict", action="store_true", help="With --status, exit 1 when any stage is incomplete")
    parser.add_argument("--reset-stage", help="Remove one stage from checkpoint state")
    parser.add_argument("--from-stage", help="Start execution from the given stage and skip earlier stages")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts for state-changing commands")
    args = parser.parse_args()

    state = _load_state(args.month)

    if args.status:
        return print_status(args.month, state, args.strict)

    if args.reset_stage:
        try:
            stage_name = _validate_stage_name(args.reset_stage)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        _confirm_or_exit(f"Reset checkpoint stage '{stage_name}'?", args.yes)
        return reset_stage(args.month, state, stage_name)

    start_index = 0
    if args.from_stage:
        try:
            from_stage = _validate_stage_name(args.from_stage)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        start_index = STAGE_ORDER.index(from_stage)
        if state["stages"].get(STAGE_STATE_KEYS[from_stage]):
            print(f"Warning: stage '{from_stage}' is already marked complete and will be rerun.")
        _confirm_or_exit(f"Skip stages before '{from_stage}' and continue?", args.yes)

    print(f"=== Monthly Publish: {args.month} ===")
    try:
        plan = load_plan(args.month)
    except FileNotFoundError as exc:
        failure_path = _write_failure_playbook(args.month, "plan_loaded", str(exc))
        print(str(exc), file=sys.stderr)
        print(f"Recovery guide: {failure_path}", file=sys.stderr)
        return 1

    stages: list[tuple[str, Callable[..., bool | None]]] = [
        ("plan_loaded", stage_plan_loaded),
        ("quality_gate", stage_quality_gate),
        ("disclosure_injected", stage_disclosure),
        ("pdf_compile", stage_pdf_compile),
        ("ghost_publish", stage_ghost_publish),
        ("newsletter", stage_newsletter),
        ("sns", stage_sns),
    ]

    for index, (stage_name, stage_fn) in enumerate(stages):
        if index < start_index:
            print(f"Skipping {stage_name} due to --from-stage")
            continue
        ok = _run_stage(stage_name, stage_fn, args, state, plan)
        _save_state(args.month, state)
        if ok is False:
            failure_path = _write_failure_playbook(
                args.month,
                stage_name,
                state.get("errors", {}).get(stage_name) or f"Stage failed: {stage_name}",
            )
            print(f"Stage failed: {stage_name}", file=sys.stderr)
            print(f"Recovery guide: {failure_path}", file=sys.stderr)
            return 1
        time.sleep(0.01)

    report_path = write_report(args.month, state, plan)
    print(f"Completed. State: {_state_path(args.month)}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
