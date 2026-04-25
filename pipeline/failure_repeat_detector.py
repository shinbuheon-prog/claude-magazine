from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from pipeline.failure_playbook import redact_sensitive_text
except ModuleNotFoundError:
    from failure_playbook import redact_sensitive_text  # type: ignore

DEFAULT_WINDOW_DAYS = 14
DEFAULT_THRESHOLD = 3
REPORTS_DIR = Path(os.environ.get("CLAUDE_MAGAZINE_REPORTS_DIR") or (ROOT / "reports"))
QUEUE_DIR = REPORTS_DIR / "auto_trigger_queue"
ARCHIVE_DIR = QUEUE_DIR / "archived"

FAILURE_REPORT_RE = re.compile(r"^failure_(?P<month>\d{4}-\d{2})_(?P<stage>[a-z_]+)\.md$")
FAILURE_TIME_RE = re.compile(r"^- Failure time:\s*(.+)$", re.MULTILINE)
MATCHED_CLASS_RE = re.compile(r"^- Matched class:\s*(.+)$", re.MULTILINE)
ERROR_BLOCK_RE = re.compile(r"## Error Output\s+```text\s*(.*?)\s*```", re.DOTALL)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def resolve_window_days(value: int | None = None) -> int:
    return value if isinstance(value, int) and value > 0 else _env_int("CLAUDE_MAGAZINE_FAILURE_WINDOW_DAYS", DEFAULT_WINDOW_DAYS)


def resolve_threshold(value: int | None = None) -> int:
    return value if isinstance(value, int) and value > 0 else _env_int("CLAUDE_MAGAZINE_FAILURE_THRESHOLD", DEFAULT_THRESHOLD)


def _report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(path for path in REPORTS_DIR.glob("failure_*.md") if path.is_file())


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_timestamp(text: str | None) -> datetime | None:
    if not text:
        return None
    cleaned = text.strip()
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_excerpt(report_text: str) -> str:
    match = ERROR_BLOCK_RE.search(report_text)
    if not match:
        return ""
    return redact_sensitive_text(match.group(1).strip())[:240]


def _parse_failure_report(path: Path) -> dict[str, Any] | None:
    match = FAILURE_REPORT_RE.match(path.name)
    if not match:
        return None
    text = path.read_text(encoding="utf-8-sig")
    failure_time_match = FAILURE_TIME_RE.search(text)
    failure_class_match = MATCHED_CLASS_RE.search(text)
    timestamp = _parse_timestamp(failure_time_match.group(1) if failure_time_match else None)
    failure_class = (failure_class_match.group(1).strip() if failure_class_match else "generic_fallback") or "generic_fallback"
    if timestamp is None:
        return None
    return {
        "month": match.group("month"),
        "stage": match.group("stage"),
        "failure_class": failure_class,
        "timestamp": timestamp.isoformat(),
        "report_path": _display_path(path),
        "error_excerpt": _extract_excerpt(text),
    }


def scan_failures(window_days: int = DEFAULT_WINDOW_DAYS) -> list[dict[str, Any]]:
    resolved_window = resolve_window_days(window_days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=resolved_window)
    failures: list[dict[str, Any]] = []
    for path in _report_files():
        parsed = _parse_failure_report(path)
        if not parsed:
            continue
        occurred_at = _parse_timestamp(parsed.get("timestamp"))
        if occurred_at is None or occurred_at < cutoff:
            continue
        failures.append(parsed)
    return sorted(failures, key=lambda item: str(item.get("timestamp")))


def count_by_class(failures: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for failure in failures:
        failure_class = str(failure.get("failure_class") or "generic_fallback")
        grouped.setdefault(failure_class, []).append(failure)
    for items in grouped.values():
        items.sort(key=lambda item: str(item.get("timestamp")))
    return grouped


def detect_repeats(
    failures: list[dict[str, Any]],
    threshold: int = DEFAULT_THRESHOLD,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> list[dict[str, Any]]:
    resolved_threshold = resolve_threshold(threshold)
    resolved_window = resolve_window_days(window_days)
    repeats: list[dict[str, Any]] = []
    for failure_class, items in count_by_class(failures).items():
        if len(items) < resolved_threshold:
            continue
        repeats.append(
            {
                "class": failure_class,
                "stage": items[-1].get("stage"),
                "count": len(items),
                "stages": sorted({str(item.get("stage")) for item in items if item.get("stage")}),
                "first_seen": items[0].get("timestamp"),
                "last_seen": items[-1].get("timestamp"),
                "occurrences": [
                    {
                        "month": item.get("month"),
                        "stage": item.get("stage"),
                        "ts": item.get("timestamp"),
                        "report_path": item.get("report_path"),
                        "error_excerpt": redact_sensitive_text(str(item.get("error_excerpt") or "")),
                    }
                    for item in items
                ],
                "window_days": resolved_window,
            }
        )
    repeats.sort(key=lambda item: (-int(item.get("count", 0)), str(item.get("class") or "")))
    return repeats


def _marker_signature(repeats: list[dict[str, Any]], window_days: int, threshold: int) -> str:
    payload = {
        "window_days": window_days,
        "threshold": threshold,
        "repeats": [
            {
                "class": repeat.get("class"),
                "count": repeat.get("count"),
                "first_seen": repeat.get("first_seen"),
                "last_seen": repeat.get("last_seen"),
                "occurrences": [
                    {
                        "month": item.get("month"),
                        "stage": item.get("stage"),
                        "ts": item.get("ts"),
                        "report_path": item.get("report_path"),
                    }
                    for item in repeat.get("occurrences", [])
                ],
            }
            for repeat in repeats
        ],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def write_queue_marker(repeats: list[dict[str, Any]], detected_at_run: str | None = None) -> Path | None:
    if not repeats:
        return None
    window_days = int(repeats[0].get("window_days") or resolve_window_days())
    threshold = resolve_threshold()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    signature = _marker_signature(repeats, window_days, threshold)

    for existing in sorted(QUEUE_DIR.glob("*.json")):
        try:
            payload = json.loads(existing.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if payload.get("status") != "queued":
            continue
        if payload.get("signature") == signature:
            return existing

    created_at = _utc_now()
    marker_path = QUEUE_DIR / f"{created_at[:10]}_{signature}.json"
    payload = {
        "created_at": created_at,
        "window_days": window_days,
        "threshold": threshold,
        "detected_at_run": detected_at_run or "manual",
        "signature": signature,
        "repeats": repeats,
        "status": "queued",
    }
    marker_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return marker_path


def acknowledge_marker(marker_path: Path) -> None:
    marker = Path(marker_path)
    if not marker.exists():
        return
    payload = json.loads(marker.read_text(encoding="utf-8-sig"))
    payload["status"] = "processed"
    payload["processed_at"] = _utc_now()
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived_path = ARCHIVE_DIR / marker.name
    archived_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    marker.unlink()


def _load_queued_markers() -> list[dict[str, Any]]:
    if not QUEUE_DIR.exists():
        return []
    markers: list[dict[str, Any]] = []
    for path in sorted(QUEUE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if payload.get("status") != "queued":
            continue
        payload["marker_path"] = str(path)
        markers.append(payload)
    return markers


def _trigger_weekly_improvement(yes: bool) -> int:
    question = "This will run weekly_improvement and may trigger an Opus call. Continue?"
    if not yes:
        answer = input(f"{question} [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            return 1
    cmd = [sys.executable, str(ROOT / "scripts" / "weekly_improvement.py")]
    completed = subprocess.run(cmd, cwd=ROOT)
    return int(completed.returncode)


def _print_text_report(repeats: list[dict[str, Any]], window_days: int, threshold: int) -> None:
    print(f"Repeated failures in last {window_days} days (threshold={threshold})")
    if not repeats:
        print("- none")
        return
    for repeat in repeats:
        stages = ", ".join(repeat.get("stages") or []) or "n/a"
        print(
            f"- {repeat.get('class')} count={repeat.get('count')} "
            f"stages={stages} last_seen={repeat.get('last_seen')}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect repeated failure classes from publish failure reports")
    parser.add_argument("--window", type=int, default=None, help="Look back N days")
    parser.add_argument("--threshold", type=int, default=None, help="Minimum repeat count")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--trigger-improvement", action="store_true", help="Queue repeats and run weekly_improvement immediately")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt for --trigger-improvement")
    args = parser.parse_args()

    window_days = resolve_window_days(args.window)
    threshold = resolve_threshold(args.threshold)
    failures = scan_failures(window_days=window_days)
    repeats = detect_repeats(failures, threshold=threshold, window_days=window_days)

    marker_path: Path | None = None
    trigger_exit_code = 0
    if args.trigger_improvement and repeats:
        marker_path = write_queue_marker(repeats, detected_at_run="failure_repeat_detector:manual")
        trigger_exit_code = _trigger_weekly_improvement(args.yes)

    payload = {
        "window_days": window_days,
        "threshold": threshold,
        "failures_scanned": len(failures),
        "repeat_count": len(repeats),
        "marker_path": str(marker_path) if marker_path else None,
        "repeats": repeats,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_text_report(repeats, window_days, threshold)
        if marker_path:
            print(f"Queued marker: {marker_path}")
    return trigger_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
