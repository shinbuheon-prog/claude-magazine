from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOK_PATH = ROOT / "spec" / "failure_playbook.yml"

REQUIRED_FAILURE_KEYS = {"class", "detector", "recovery"}
SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_-]+"), "sk-ant-***"),
    (re.compile(r"figd_[A-Za-z0-9_-]+"), "figd_***"),
    (re.compile(r"\b[a-f0-9]{24}:[a-f0-9]{64}\b", re.IGNORECASE), "kid:***"),
]


def load_failure_playbook() -> dict[str, Any]:
    payload = yaml.safe_load(PLAYBOOK_PATH.read_text(encoding="utf-8")) or {}
    validate_playbook_spec(payload)
    return payload


def validate_playbook_spec(payload: dict[str, Any]) -> None:
    stages = payload.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise ValueError("failure_playbook.yml must define a non-empty stages mapping")

    for stage_name, stage_payload in stages.items():
        if not isinstance(stage_payload, dict):
            raise ValueError(f"stage '{stage_name}' must be a mapping")
        failures = stage_payload.get("common_failures")
        if not isinstance(failures, list) or not failures:
            raise ValueError(f"stage '{stage_name}' must define common_failures")
        for index, failure in enumerate(failures, start=1):
            if not isinstance(failure, dict):
                raise ValueError(f"stage '{stage_name}' failure #{index} must be a mapping")
            missing = REQUIRED_FAILURE_KEYS - set(failure)
            if missing:
                raise ValueError(f"stage '{stage_name}' failure #{index} missing keys: {sorted(missing)}")
            if not isinstance(failure["recovery"], list) or not failure["recovery"]:
                raise ValueError(f"stage '{stage_name}' failure '{failure['class']}' must define recovery steps")


def redact_sensitive_text(text: str) -> str:
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _stage_entries(stage: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    source = payload or load_failure_playbook()
    stages = source.get("stages") or {}
    stage_payload = stages.get(stage) or {}
    return list(stage_payload.get("common_failures") or [])


def match_failure_class(stage: str, error_output: str, payload: dict[str, Any] | None = None) -> str | None:
    text = redact_sensitive_text(error_output)
    for entry in _stage_entries(stage, payload):
        detector = str(entry.get("detector") or "")
        if detector and re.search(detector, text, flags=re.IGNORECASE):
            return str(entry["class"])
    return None


def _entry_for(stage: str, failure_class: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for entry in _stage_entries(stage, payload):
        if entry.get("class") == failure_class:
            return entry
    return None


def render_playbook(stage: str, failure_class: str | None, context: dict[str, Any], payload: dict[str, Any] | None = None) -> str:
    source = payload or load_failure_playbook()
    failure_class = failure_class or "generic_fallback"
    entry = _entry_for(stage, failure_class, source)
    recovery_steps = entry.get("recovery") if entry else [
        "Inspect the latest logs and state file",
        "Run scripts/check_env.py --dry-run to verify local configuration",
        f"Reset and rerun the stage once the root cause is fixed",
    ]
    month = context.get("month", "unknown")
    state_path = context.get("state_path", f"reports/publish_state_{month}.json")
    resume_stage = context.get("resume_stage", stage)
    error_output = redact_sensitive_text(str(context.get("error_output") or "")).strip()

    lines = [
        "# Publish Failure Recovery Guide",
        "",
        f"- Month: {month}",
        f"- Failed stage: {stage}",
        f"- Failure time: {context.get('failed_at')}",
        f"- Matched class: {failure_class}",
        "",
        "## Recovery Checklist",
    ]
    for step in recovery_steps:
        lines.append(f"- [ ] {step.replace('<month>', str(month))}")
    lines.extend(
        [
            "",
            "## Retry Commands",
            "",
            "```bash",
            f"python scripts/publish_monthly.py --month {month} --reset-stage {resume_stage} --yes",
            f"python scripts/publish_monthly.py --month {month}",
            "```",
            "",
            "## References",
            "",
            f"- {state_path}",
            "",
            "## Error Output",
            "",
            "```text",
            error_output or "(no captured error output)",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def render_catalog(payload: dict[str, Any] | None = None) -> str:
    source = payload or load_failure_playbook()
    lines = [
        "# Failure Playbook Catalog",
        "",
        "Generated from `spec/failure_playbook.yml`.",
        "",
    ]
    for stage, stage_payload in (source.get("stages") or {}).items():
        lines.append(f"## {stage}")
        lines.append("")
        for entry in stage_payload.get("common_failures", []):
            lines.append(f"- `{entry['class']}`: `{entry['detector']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_failure_report(month: str, stage: str, error_output: str, state_path: str | Path) -> str:
    payload = load_failure_playbook()
    failure_class = match_failure_class(stage, error_output, payload) or "generic_fallback"
    return render_playbook(
        stage,
        failure_class,
        {
            "month": month,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error_output": error_output,
            "state_path": str(state_path),
            "resume_stage": stage,
        },
        payload,
    )
