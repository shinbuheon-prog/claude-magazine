"""
Fact checker.

Model:
- default: Claude Opus 4.7 via provider abstraction

TASK_044:
- prompt caching on API provider for static rules and source document bundle

TASK_045:
- Citations API path for API provider
- citations payload persisted under data/citations/<article_id>.json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    from pipeline.observability import log_usage, start_trace
except ModuleNotFoundError:
    from observability import log_usage, start_trace

try:
    from pipeline.heuristics_injector import inject_heuristics
except ModuleNotFoundError:
    try:
        from heuristics_injector import inject_heuristics  # type: ignore
    except ModuleNotFoundError:
        def inject_heuristics(category: str, max_examples: int = 10) -> str:
            return ""

if sys.platform == "win32" and not getattr(sys.stdout, "_utf8_wrapped", False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stdout._utf8_wrapped = True  # type: ignore[attr-defined]
        sys.stderr._utf8_wrapped = True  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

load_dotenv()

ROOT = Path(__file__).parent.parent
PROMPTS_DIR = ROOT / "prompts"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

SOURCE_FETCH_TIMEOUT = 15
MAX_SOURCE_CHARS = 18000


def load_template() -> str:
    return (PROMPTS_DIR / "template_C_factcheck.txt").read_text(encoding="utf-8")


def _clean_source_text(raw_text: str) -> str:
    soup = BeautifulSoup(raw_text, "html.parser")
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _fetch_source_text(url: str) -> str:
    response = requests.get(url, timeout=SOURCE_FETCH_TIMEOUT)
    response.raise_for_status()
    cleaned = _clean_source_text(response.text)
    return cleaned[:MAX_SOURCE_CHARS]


def load_sources_for_article(article_id: str | None) -> str:
    if not article_id:
        return "(source registry not connected for this run)"

    try:
        from pipeline.source_registry import list_sources
    except ModuleNotFoundError:
        from source_registry import list_sources  # type: ignore

    sources = list_sources(article_id)
    if not sources:
        return f"(no registered sources for article_id={article_id})"

    lines = []
    for source in sources:
        lines.append(f"[{source['source_id']}] {source['publisher']} | {source['url']}")
    return "\n".join(lines)


def _build_system_blocks(category: str) -> list[dict[str, Any]]:
    heuristics_block = inject_heuristics(category)
    rules_text = (
        "당신은 팩트체크 편집자다.\n"
        "초안의 각 주장 문장을 제공된 출처와 대조해 아래 4가지 중 하나로 판정한다.\n"
        "1) 확인됨\n"
        "2) 과장됨\n"
        "3) 출처 불충분\n"
        "4) 수정 필요\n"
        "가능하면 모든 핵심 판단에 citations를 사용하라."
    )
    blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": rules_text,
        }
    ]
    if heuristics_block:
        blocks.append(
            {
                "type": "text",
                "text": heuristics_block,
                "cache_control": {"type": "ephemeral"},
            }
        )
    else:
        blocks[0]["cache_control"] = {"type": "ephemeral"}
    return blocks


def _build_plain_messages(template: str, draft_text: str, source_bundle: str) -> list[dict[str, Any]]:
    user_prompt = template.replace("{{draft_text}}", draft_text).replace("{{source_bundle}}", source_bundle)
    return [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}]


def _build_citation_messages(article_id: str, draft_text: str, template: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from pipeline.source_registry import list_sources
    except ModuleNotFoundError:
        from source_registry import list_sources  # type: ignore

    sources = list_sources(article_id)
    if not sources:
        raise RuntimeError(f"no registered sources for article_id={article_id}")

    content_blocks: list[dict[str, Any]] = []
    document_map: list[dict[str, Any]] = []
    fetched = 0
    for source in sources:
        try:
            source_text = _fetch_source_text(source["url"])
        except Exception:
            continue
        if not source_text:
            continue
        block: dict[str, Any] = {
            "type": "document",
            "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": source_text,
            },
            "title": f"{source['source_id']} | {source['publisher']}",
            "context": source["url"],
            "citations": {"enabled": True},
        }
        content_blocks.append(block)
        document_map.append(
            {
                "doc_index": fetched,
                "source_id": source["source_id"],
                "url": source["url"],
                "publisher": source["publisher"],
            }
        )
        fetched += 1

    if not content_blocks:
        raise RuntimeError(f"unable to fetch usable source documents for article_id={article_id}")

    content_blocks[-1]["cache_control"] = {"type": "ephemeral"}
    user_prompt = (
        template.replace("{{draft_text}}", draft_text).replace("{{source_bundle}}", "documents attached above")
        + "\n\n모든 핵심 판단 문장에는 가능한 한 citations를 사용하라."
    )
    content_blocks.append({"type": "text", "text": user_prompt})
    return [{"role": "user", "content": content_blocks}], document_map


def _write_log(
    *,
    request_id: str | None,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    provider: str,
    model: str,
    citations_path: Path | None,
) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read_tokens,
        "cache_creation_input_tokens": cache_creation_tokens,
        "citations_path": str(citations_path.relative_to(ROOT)) if citations_path else None,
    }
    log_file = LOGS_DIR / f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} -> {log_file.name}", file=sys.stderr)
    return log_file


def run_factcheck(draft_text: str, source_bundle: str, *, article_id: str | None = None, category: str = "all") -> str:
    try:
        from pipeline.citations_store import save_citations
        from pipeline.claude_provider import get_provider
    except ModuleNotFoundError:
        from citations_store import save_citations  # type: ignore
        from claude_provider import get_provider  # type: ignore

    provider = get_provider()
    template = load_template()
    system_blocks = _build_system_blocks(category)
    messages = _build_plain_messages(template, draft_text, source_bundle)
    document_map: list[dict[str, Any]] = []
    use_citations = provider.name == "api" and bool(article_id)

    if use_citations:
        try:
            messages, document_map = _build_citation_messages(article_id or "", draft_text, template)
        except Exception as exc:
            print(f"[warn] citations path unavailable, falling back to plain prompt: {type(exc).__name__}: {exc}", file=sys.stderr)
            use_citations = False

    trace = start_trace(name="fact_checking", model=f"opus-via-{provider.name}")

    def _stream_print(chunk: str) -> None:
        try:
            print(chunk, end="", flush=True)
        except UnicodeEncodeError:
            pass

    result = provider.complete_with_blocks(
        system_blocks=system_blocks,
        messages=messages,
        model_tier="opus",
        max_tokens=8000,
        stream=not use_citations,
        stream_callback=_stream_print,
    )
    if not use_citations:
        print()

    citations_path: Path | None = None
    if use_citations and result.raw is not None and article_id:
        citations_path = save_citations(
            article_id=article_id,
            request_id=result.request_id,
            provider=result.provider,
            model=result.model or "claude-opus-4-7",
            document_map=document_map,
            raw_response=result.raw,
        )

    log_usage(
        getattr(trace, "id", None),
        result.input_tokens,
        result.output_tokens,
        result.model or "claude-opus-4-7",
        request_id=result.request_id,
    )
    _write_log(
        request_id=result.request_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cache_read_tokens=result.cache_read_tokens,
        cache_creation_tokens=result.cache_creation_tokens,
        provider=result.provider,
        model=result.model or "claude-opus-4-7",
        citations_path=citations_path,
    )
    return result.text


def dry_run_preview(draft_text: str, source_bundle: str, category: str = "all") -> None:
    template = load_template()
    system_blocks = _build_system_blocks(category)
    messages = _build_plain_messages(template, draft_text, source_bundle)

    print("=" * 60)
    print("[DRY-RUN] SYSTEM BLOCKS")
    print("=" * 60)
    print(json.dumps(system_blocks, ensure_ascii=False, indent=2))
    print()
    print("=" * 60)
    print("[DRY-RUN] MESSAGES")
    print("=" * 60)
    print(json.dumps(messages, ensure_ascii=False, indent=2))
    print()
    print("[DRY-RUN] finished without API call")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fact checker")
    parser.add_argument("--draft", required=True, help="draft markdown path")
    parser.add_argument("--article-id", help="source registry article id")
    parser.add_argument("--category", default="all", help="editor heuristics category")
    parser.add_argument("--out", help="result output path")
    parser.add_argument("--dry-run", action="store_true", help="show prompts without API call")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8-sig")
    source_bundle = load_sources_for_article(args.article_id)

    if args.dry_run:
        dry_run_preview(draft_text, source_bundle, category=args.category)
        return

    print("=== factcheck start ===", file=sys.stderr)
    result = run_factcheck(
        draft_text,
        source_bundle,
        article_id=args.article_id,
        category=args.category,
    )
    out_path = args.out or str(LOGS_DIR / f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    Path(out_path).write_text(result, encoding="utf-8")
    print(f"\n[done] factcheck output saved: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
