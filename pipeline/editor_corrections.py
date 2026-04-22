"""
Editorial correction storage and summarization utilities (TASK_026).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "editor_corrections.db"

VALID_CORRECTION_TYPES = {
    "exaggeration",
    "tone",
    "factual",
    "source",
    "structure",
    "style",
    "clarity",
}
VALID_SEVERITIES = {"low", "medium", "high"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    article_id TEXT,
    category TEXT,
    correction_type TEXT NOT NULL,
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    editor_note TEXT,
    severity TEXT DEFAULT 'medium',
    tags TEXT,
    source_commit TEXT
);

CREATE INDEX IF NOT EXISTS idx_correction_type ON corrections(correction_type);
CREATE INDEX IF NOT EXISTS idx_category ON corrections(category);
CREATE INDEX IF NOT EXISTS idx_timestamp ON corrections(timestamp);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_tags(tags: list[str] | None) -> str | None:
    if not tags:
        return None
    cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
    return ",".join(dict.fromkeys(cleaned)) or None


def _validate_inputs(correction_type: str, severity: str) -> None:
    if correction_type not in VALID_CORRECTION_TYPES:
        raise ValueError(f"Unsupported correction_type: {correction_type}")
    if severity not in VALID_SEVERITIES:
        raise ValueError(f"Unsupported severity: {severity}")


def _ensure_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)


def _connect() -> sqlite3.Connection:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _current_commit_hash() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def record_correction(
    article_id: str,
    category: str,
    correction_type: str,
    original: str,
    corrected: str,
    editor_note: str | None = None,
    severity: str = "medium",
    tags: list[str] | None = None,
) -> int:
    """Record an editorial correction in SQLite and return its row id."""
    _validate_inputs(correction_type, severity)
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO corrections (
                timestamp, article_id, category, correction_type,
                original_text, corrected_text, editor_note, severity, tags, source_commit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                article_id or None,
                category or None,
                correction_type,
                original,
                corrected,
                editor_note,
                severity,
                _normalize_tags(tags),
                _current_commit_hash(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def query_corrections(
    category: str | None = None,
    correction_type: str | None = None,
    since_days: int = 90,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query recent corrections, newest first."""
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    clauses = ["timestamp >= ?"]
    params: list[Any] = [since.isoformat()]

    if category and category != "all":
        clauses.append("category = ?")
        params.append(category)
    if correction_type:
        clauses.append("correction_type = ?")
        params.append(correction_type)

    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM corrections
            WHERE {' AND '.join(clauses)}
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def summarize_for_prompt(category: str, max_examples: int = 10) -> str:
    """
    Build a deterministic markdown summary for prompt injection.
    """
    rows = query_corrections(category=category, since_days=90, limit=max(max_examples * 3, 30))
    if not rows:
        scope = category if category and category != "all" else "all"
        return (
            "---\n"
            f"## Editorial Corrections Memory ({scope})\n\n"
            "No prior corrections recorded yet.\n"
            "---"
        )

    ranked = sorted(
        rows,
        key=lambda row: (
            SEVERITY_ORDER.get(str(row.get("severity") or "medium"), 1),
            str(row.get("timestamp") or ""),
        ),
    )
    selected = ranked[:max_examples]
    heading = category if category and category != "all" else "all categories"
    lines = [
        "---",
        f"## Editorial Corrections Memory ({heading}, {len(rows)} recent records -> {len(selected)} examples)",
        "",
        "Use these as editorial guardrails. Prefer the corrected phrasing and avoid repeating the original issue patterns.",
        "",
    ]
    for index, row in enumerate(selected, start=1):
        tags = row.get("tags") or ""
        tags_suffix = f" | tags: {tags}" if tags else ""
        note = row.get("editor_note") or "No note provided."
        lines.append(
            f"{index}. [{row['correction_type']}/{row['severity']}] "
            f"\"{row['original_text']}\" -> \"{row['corrected_text']}\"{tags_suffix}"
        )
        lines.append(f"   Why: {note}")
    lines.extend(["", "---"])
    return "\n".join(lines)


def _cli_add(args: argparse.Namespace) -> int:
    correction_id = record_correction(
        article_id=args.article_id or "",
        category=args.category or "",
        correction_type=args.type,
        original=args.original,
        corrected=args.corrected,
        editor_note=args.note,
        severity=args.severity,
        tags=args.tags.split(",") if args.tags else None,
    )
    print(json.dumps({"id": correction_id, "db_path": str(DB_PATH)}, ensure_ascii=False))
    return 0


def _cli_list(args: argparse.Namespace) -> int:
    rows = query_corrections(
        category=args.category,
        correction_type=args.type,
        since_days=args.since_days,
        limit=args.limit,
    )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def _cli_summary(args: argparse.Namespace) -> int:
    print(summarize_for_prompt(args.category, max_examples=args.max_examples))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Editorial correction memory store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Record a correction")
    add_parser.add_argument("--article-id", default="")
    add_parser.add_argument("--category", default="")
    add_parser.add_argument("--type", required=True, choices=sorted(VALID_CORRECTION_TYPES))
    add_parser.add_argument("--original", required=True)
    add_parser.add_argument("--corrected", required=True)
    add_parser.add_argument("--note")
    add_parser.add_argument("--severity", default="medium", choices=sorted(VALID_SEVERITIES))
    add_parser.add_argument("--tags", help="Comma-separated tags")
    add_parser.set_defaults(handler=_cli_add)

    list_parser = subparsers.add_parser("list", help="List recent corrections")
    list_parser.add_argument("--category")
    list_parser.add_argument("--type", choices=sorted(VALID_CORRECTION_TYPES))
    list_parser.add_argument("--since-days", type=int, default=90)
    list_parser.add_argument("--limit", type=int, default=50)
    list_parser.set_defaults(handler=_cli_list)

    summary_parser = subparsers.add_parser("summary", help="Build prompt summary")
    summary_parser.add_argument("--category", default="all")
    summary_parser.add_argument("--max-examples", type=int, default=10)
    summary_parser.set_defaults(handler=_cli_summary)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
