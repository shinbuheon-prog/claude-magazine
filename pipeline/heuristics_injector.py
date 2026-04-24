"""
Prompt-side editorial heuristics injector (TASK_026).
"""
from __future__ import annotations

import argparse
import hashlib
from functools import lru_cache
from pathlib import Path

try:
    from pipeline.editor_corrections import DB_PATH, query_corrections, summarize_for_prompt
except ModuleNotFoundError:
    from editor_corrections import DB_PATH, query_corrections, summarize_for_prompt  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "editor_heuristics.md"


def _signature(category: str, max_examples: int) -> str:
    parts = [category, str(max_examples)]
    if DB_PATH.exists():
        stat = DB_PATH.stat()
        parts.extend([str(stat.st_mtime_ns), str(stat.st_size)])
    if PROMPT_PATH.exists():
        content = PROMPT_PATH.read_text(encoding="utf-8")
        parts.append(hashlib.sha256(content.encode("utf-8")).hexdigest())
    return "|".join(parts)


@lru_cache(maxsize=32)
def _inject_cached(category: str, max_examples: int, signature: str) -> str:
    del signature
    seed = PROMPT_PATH.read_text(encoding="utf-8").strip() if PROMPT_PATH.exists() else ""
    if not seed and not query_corrections(category=category, since_days=3650, limit=1):
        return ""
    summary = summarize_for_prompt(category=category, max_examples=max_examples).strip()
    chunks = [chunk for chunk in [seed, summary] if chunk]
    if not chunks:
        return ""
    return "\n\n".join(chunks)


def inject_heuristics(category: str, max_examples: int = 10) -> str:
    category_key = category or "all"
    return _inject_cached(category_key, max_examples, _signature(category_key, max_examples))


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview prompt heuristics block")
    subparsers = parser.add_subparsers(dest="command", required=True)
    preview = subparsers.add_parser("preview", help="Preview injected heuristics")
    preview.add_argument("--category", default="all")
    preview.add_argument("--max-examples", type=int, default=10)
    args = parser.parse_args()
    print(inject_heuristics(args.category, max_examples=args.max_examples))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
