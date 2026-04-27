from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "source_registry.db"
LOGS_DIR = ROOT / "logs"
QUOTE_LIMIT = 200

PROMPT_ONELINER = """제목: {title}

본문 일부:
{body_preview}

위 source를 50자 이내 한 줄로 요약하라. 설명 없이 요약문만 출력한다."""

PROMPT_3LINE = """제목: {title}

본문:
{body}

위 source를 정확히 3줄로 요약하라.
1. 핵심 변화
2. 중요한 맥락
3. 매거진 활용 포인트"""

PROMPT_QUOTES = """제목: {title}

본문:
{body}

매거진에서 인용 가능한 핵심 구절 3~5개를 JSON list로 출력하라.
형식:
[{{"quote": "...", "context": "...", "page_or_section": "..."}}]
설명 문장은 금지한다."""


def _get_provider():
    from pipeline.claude_provider import get_provider

    return get_provider()


def _ensure_schema() -> None:
    from pipeline.source_registry import init_db

    init_db()


def _fetch_source(source_id: str) -> dict[str, Any]:
    _ensure_schema()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
        if row is None:
            raise KeyError(f"source not found: {source_id}")
        return dict(row)
    finally:
        conn.close()


def _append_log(payload: dict[str, Any]) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGS_DIR / f"auto_summarizer_{datetime.now(timezone.utc):%Y%m%d}.json"
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except Exception:
            existing = []
    existing.append(payload)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _safe_json_list(text: str) -> list[dict[str, Any]]:
    match = re.search(r"\[[\s\S]*\]", text or "")
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _truncate_quotes(quotes: list[dict[str, Any]], quote_limit: int) -> list[dict[str, Any]]:
    limited: list[dict[str, Any]] = []
    effective_limit = max(1, int(quote_limit or QUOTE_LIMIT))
    for item in quotes:
        quote = str(item.get("quote") or "")
        if len(quote) > effective_limit:
            quote = quote[:effective_limit].rstrip() + "..."
        limited.append(
            {
                "quote": quote,
                "context": str(item.get("context") or ""),
                "page_or_section": str(item.get("page_or_section") or ""),
            }
        )
    return limited


def _call_llm(prompt: str, model_tier: str, max_tokens: int) -> tuple[str, dict[str, Any]]:
    provider = _get_provider()
    result = provider.stream_complete(
        system="You are a concise editorial summarizer.",
        user=prompt,
        model_tier=model_tier,
        max_tokens=max_tokens,
    )
    meta = {
        "request_id": result.request_id,
        "model": result.model,
        "provider": result.provider,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cache_read_tokens": result.cache_read_tokens,
    }
    return result.text.strip(), meta


def summarize_source(
    source_id: str,
    levels: tuple[str, ...] = ("oneliner", "3line", "quotes"),
    dry_run: bool = False,
) -> dict[str, Any]:
    source = _fetch_source(source_id)
    title = str(source.get("title") or source.get("url") or source_id)
    body = str(source.get("content_body") or source.get("content_preview") or "")
    body_preview = body[:500]
    quote_limit = int(source.get("quote_limit") or QUOTE_LIMIT)

    result: dict[str, Any] = {
        "source_id": source_id,
        "summary_oneliner": source.get("summary_oneliner") or "",
        "summary_3line": source.get("summary_3line") or "",
        "key_quotes": json.loads(source.get("key_quotes") or "[]"),
        "total_tokens": 0,
        "request_id": None,
        "dry_run": dry_run,
    }
    log_entries: list[dict[str, Any]] = []

    if dry_run:
        for level in levels:
            prompt = {
                "oneliner": PROMPT_ONELINER.format(title=title, body_preview=body_preview),
                "3line": PROMPT_3LINE.format(title=title, body=body[:5000]),
                "quotes": PROMPT_QUOTES.format(title=title, body=body[:5000]),
            }[level]
            result["total_tokens"] += _estimate_tokens("You are a concise editorial summarizer.\n" + prompt)
        return result

    if "oneliner" in levels:
        text, meta = _call_llm(PROMPT_ONELINER.format(title=title, body_preview=body_preview), "haiku", 80)
        result["summary_oneliner"] = text[:50].strip()
        result["total_tokens"] += meta["input_tokens"] + meta["output_tokens"]
        result["request_id"] = meta["request_id"] or result["request_id"]
        log_entries.append({"level": "oneliner", **meta, "source_id": source_id})

    if "3line" in levels:
        text, meta = _call_llm(PROMPT_3LINE.format(title=title, body=body[:5000]), "sonnet", 220)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        result["summary_3line"] = "\n".join(lines[:3])
        result["total_tokens"] += meta["input_tokens"] + meta["output_tokens"]
        result["request_id"] = meta["request_id"] or result["request_id"]
        log_entries.append({"level": "3line", **meta, "source_id": source_id})

    if "quotes" in levels:
        text, meta = _call_llm(PROMPT_QUOTES.format(title=title, body=body[:5000]), "sonnet", 500)
        quotes = _truncate_quotes(_safe_json_list(text), quote_limit)
        result["key_quotes"] = quotes
        result["total_tokens"] += meta["input_tokens"] + meta["output_tokens"]
        result["request_id"] = meta["request_id"] or result["request_id"]
        log_entries.append({"level": "quotes", **meta, "source_id": source_id})

    from pipeline.source_registry import update_source

    timestamp = datetime.now(timezone.utc).isoformat()
    update_source(
        source_id,
        summary_oneliner=result["summary_oneliner"],
        summary_3line=result["summary_3line"],
        key_quotes=result["key_quotes"],
        summarized_at=timestamp,
    )
    for entry in log_entries:
        _append_log(entry)
    return result


def batch_summarize_pending(
    article_id_filter: str | None = None,
    max_count: int = 100,
    since_days: int | None = None,
    topic: str | None = None,
    levels: tuple[str, ...] = ("oneliner", "3line", "quotes"),
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    _ensure_schema()
    clauses = ["COALESCE(summary_oneliner, '') = ''"]
    params: list[Any] = []
    if article_id_filter:
        clauses.append("article_id = ?")
        params.append(article_id_filter)
    if since_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
        clauses.append("retrieved_at >= ?")
        params.append(cutoff)
    if topic:
        clauses.append("topics LIKE ?")
        params.append(f"%{topic}%")

    sql = (
        "SELECT source_id FROM sources "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY retrieved_at ASC LIMIT ?"
    )
    params.append(max(1, int(max_count)))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return [summarize_source(row["source_id"], levels=levels, dry_run=dry_run) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize registered sources")
    parser.add_argument("--source-id")
    parser.add_argument("--article-id")
    parser.add_argument("--since-days", type=int)
    parser.add_argument("--topic")
    parser.add_argument("--levels", default="oneliner,3line,quotes")
    parser.add_argument("--max-count", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    levels = tuple(part.strip() for part in args.levels.split(",") if part.strip())
    if args.source_id:
        payload = summarize_source(args.source_id, levels=levels, dry_run=args.dry_run)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    payload = batch_summarize_pending(
        article_id_filter=args.article_id,
        since_days=args.since_days,
        topic=args.topic,
        max_count=args.max_count,
        levels=levels,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
