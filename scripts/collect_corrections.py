"""
Collect editorial corrections from git diffs and store them in TASK_026 SQLite.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from pipeline.editor_corrections import VALID_CORRECTION_TYPES, VALID_SEVERITIES, record_correction
except ModuleNotFoundError:
    from editor_corrections import VALID_CORRECTION_TYPES, VALID_SEVERITIES, record_correction  # type: ignore

HUNK_RE = re.compile(r"^@@ -(?P<old>\d+)(?:,\d+)? \+(?P<new>\d+)(?:,\d+)? @@")


@dataclass
class CorrectionCandidate:
    path: str
    removed: str
    added: str
    source_commit: str


def _run_git_diff(since: str, until: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", since, until, "--", "drafts"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _parse_diff(diff_text: str, source_commit: str) -> list[CorrectionCandidate]:
    candidates: list[CorrectionCandidate] = []
    current_path = ""
    removed_lines: list[str] = []
    added_lines: list[str] = []

    def flush() -> None:
        nonlocal removed_lines, added_lines
        removed = "\n".join(line for line in removed_lines if line.strip())
        added = "\n".join(line for line in added_lines if line.strip())
        if current_path and removed and added:
            candidates.append(
                CorrectionCandidate(
                    path=current_path,
                    removed=removed,
                    added=added,
                    source_commit=source_commit,
                )
            )
        removed_lines = []
        added_lines = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            flush()
            continue
        if line.startswith("+++ b/"):
            current_path = line[6:]
            continue
        if HUNK_RE.match(line):
            flush()
            continue
        if line.startswith("-") and not line.startswith("---"):
            removed_lines.append(line[1:])
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])
            continue
    flush()
    return candidates


def _infer_category(path: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    stem = Path(path).stem.lower()
    if "interview" in stem:
        return "interview"
    if "deep" in stem or "insight" in stem:
        return "deep_dive"
    return "all"


def _auto_classify(candidate: CorrectionCandidate) -> tuple[str, str, str | None]:
    haiku = _haiku_classify(candidate)
    if haiku is not None:
        return haiku

    removed = candidate.removed
    added = candidate.added
    lowered_removed = removed.lower()
    note = "auto classified from git diff"

    if any(token in lowered_removed for token in ("최초", "유일", "완벽", "압도", "폭발")):
        return "exaggeration", "high", "Overstatement softened."
    if any(char.isdigit() for char in removed + added):
        return "factual", "high", "Numeric or factual wording changed."
    if "(" in removed or ")" in removed or "src-" in lowered_removed:
        return "source", "medium", "Source or attribution wording changed."
    if len(removed.splitlines()) != len(added.splitlines()):
        return "structure", "medium", note
    if len(added) < len(removed):
        return "clarity", "medium", note
    return "style", "low", note


def _haiku_classify(candidate: CorrectionCandidate) -> tuple[str, str, str | None] | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None

    prompt = {
        "path": candidate.path,
        "original": candidate.removed,
        "corrected": candidate.added,
        "valid_types": sorted(VALID_CORRECTION_TYPES),
        "valid_severities": sorted(VALID_SEVERITIES),
    }
    client = anthropic.Anthropic(api_key=api_key, timeout=5.0)
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=(
                "Classify editorial corrections. Return JSON only with keys "
                "correction_type, severity, editor_note."
            ),
            messages=[{"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        payload = json.loads(text)
        correction_type = str(payload["correction_type"])
        severity = str(payload["severity"])
        note = payload.get("editor_note")
        if correction_type not in VALID_CORRECTION_TYPES or severity not in VALID_SEVERITIES:
            return None
        return correction_type, severity, str(note) if note else None
    except Exception:
        return None


def _interactive_metadata(candidate: CorrectionCandidate) -> tuple[str, str, str | None]:
    print(f"\nPath: {candidate.path}")
    print(f"- original: {candidate.removed}")
    print(f"+ corrected: {candidate.added}")
    correction_type = input(
        f"type {sorted(VALID_CORRECTION_TYPES)}: "
    ).strip()
    while correction_type not in VALID_CORRECTION_TYPES:
        correction_type = input("enter a valid type: ").strip()
    severity = input(f"severity {sorted(VALID_SEVERITIES)} [medium]: ").strip() or "medium"
    while severity not in VALID_SEVERITIES:
        severity = input("enter a valid severity: ").strip()
    note = input("editor note (optional): ").strip() or None
    return correction_type, severity, note


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect editorial corrections from git diff")
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", default="HEAD")
    parser.add_argument("--category")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true")
    mode.add_argument("--auto", action="store_true")
    parser.add_argument("--article-id", default="")
    parser.add_argument("--tags", default="")
    args = parser.parse_args()

    diff_text = _run_git_diff(args.since, args.until)
    candidates = _parse_diff(diff_text, source_commit=args.until)
    if not candidates:
        print("No draft corrections found.")
        return 0

    total = 0
    for candidate in candidates:
        if args.interactive:
            correction_type, severity, note = _interactive_metadata(candidate)
        else:
            correction_type, severity, note = _auto_classify(candidate)
        correction_id = record_correction(
            article_id=args.article_id,
            category=_infer_category(candidate.path, args.category),
            correction_type=correction_type,
            original=candidate.removed,
            corrected=candidate.added,
            editor_note=note,
            severity=severity,
            tags=[tag.strip() for tag in args.tags.split(",") if tag.strip()] or None,
        )
        print(f"recorded correction #{correction_id} from {candidate.path}")
        total += 1
    print(f"total recorded: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
