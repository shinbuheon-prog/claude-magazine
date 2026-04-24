"""
섹션 초안 생성기
모델: claude-sonnet-4-6
사용법: python pipeline/draft_writer.py --brief brief.json --section "섹션명" [--out draft.md] [--dry-run]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

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

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
DRAFTS_DIR = ROOT / "drafts"
LOGS_DIR = ROOT / "logs"
DRAFTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def load_template() -> str:
    return (PROMPTS_DIR / "template_B_draft.txt").read_text(encoding="utf-8")


def _cache_threshold(model_tier: str) -> int:
    return {"opus": 4096, "sonnet": 2048, "haiku": 4096}.get(model_tier, 2048)


def _should_cache_system(provider, system_blocks: list[dict], messages: list[dict], model_tier: str) -> bool:
    if getattr(provider, "name", "") != "api":
        return False
    try:
        tokens = provider.count_tokens(system_blocks=system_blocks, messages=messages, model_tier=model_tier)
    except Exception:
        return False
    return tokens >= _cache_threshold(model_tier)


def _write_log(
    section_name: str,
    request_id: str | None,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_enabled: bool = False,
) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-sonnet-4-6",
        "section": section_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read_tokens,
        "cache_creation_input_tokens": cache_creation_tokens,
        "cache_enabled": cache_enabled,
    }
    log_file = LOGS_DIR / f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} -> {log_file.name}", file=sys.stderr)
    return log_file


def _validate_source_markers(draft_text: str) -> None:
    if not re.search(r"\((?:src-[a-z0-9]{8}|UNKNOWN)\)", draft_text):
        raise ValueError("초안에 '(source_id)' 또는 '(UNKNOWN)' 표기가 없습니다.")


def _build_dry_run_draft(brief: dict, section_name: str) -> str:
    source_id = "UNKNOWN"
    for item in brief.get("evidence_map", []):
        candidate = item.get("source_id")
        if isinstance(candidate, str) and candidate:
            source_id = candidate
            break

    return (
        f"## {section_name}\n\n"
        f"{brief.get('angle', '핵심 관점을 요약한다.')} ({source_id})\n\n"
        f"{brief.get('why_now', '지금 중요한 이유를 정리한다.')} ({source_id})\n"
    )


def _derive_article_id(brief: dict, section_name: str) -> str:
    base = str(
        brief.get("article_id")
        or brief.get("slug")
        or brief.get("working_title")
        or section_name
    )
    slug = re.sub(r"[^\w\s-]", " ", base, flags=re.UNICODE)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-").lower()
    return slug[:50] or "article"


def write_section(brief: dict, section_name: str, source_bundle: str = "", dry_run: bool = False) -> str:
    if dry_run:
        draft_text = _build_dry_run_draft(brief, section_name)
        _validate_source_markers(draft_text)
        _write_log(section_name, "dry-run", 0, 0)
        return draft_text

    # TASK_033: provider 추상화
    try:
        from pipeline.claude_provider import get_provider
    except ModuleNotFoundError:
        from claude_provider import get_provider  # type: ignore

    provider = get_provider()
    template = load_template()
    heuristics_block = inject_heuristics(str(brief.get("category") or "all"))
    system_prompt = (
        "당신은 신중한 기술 저널리스트다.\n"
        "한국어로만 작성하라.\n"
        "각 문단은 하나의 결론만 다룬다.\n"
        "출처 없는 단정은 금지한다."
    )
    if heuristics_block:
        system_prompt += "\n\n" + heuristics_block
    user_prompt = (
        template.replace("{{approved_brief}}", json.dumps(brief, ensure_ascii=False, indent=2))
        .replace("{{section_name}}", section_name)
        .replace("{{source_bundle}}", source_bundle or "(소스 묶음 없음)")
    )

    trace = start_trace(
        name="draft_writing",
        model=f"sonnet-via-{provider.name}",
        topic=str(brief.get("working_title", "")),
    )

    def _stream_print(chunk: str) -> None:
        try:
            print(chunk, end="", flush=True)
        except UnicodeEncodeError:
            pass  # Windows cp949 특수문자 skip

    system_blocks = [{"type": "text", "text": system_prompt}]
    messages = [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}]
    cache_enabled = _should_cache_system(provider, system_blocks, messages, "sonnet")
    if cache_enabled:
        system_blocks[-1]["cache_control"] = {"type": "ephemeral"}

    result = provider.complete_with_blocks(
        system_blocks=system_blocks,
        messages=messages,
        model_tier="sonnet",
        max_tokens=6000,
        stream=True,
        stream_callback=_stream_print,
    )
    print()
    draft_text = result.text

    _validate_source_markers(draft_text)
    log_usage(
        getattr(trace, "id", None),
        result.input_tokens,
        result.output_tokens,
        result.model or "claude-sonnet-4-6",
        request_id=result.request_id,
    )
    _write_log(
        section_name,
        result.request_id,
        result.input_tokens,
        result.output_tokens,
        cache_read_tokens=result.cache_read_tokens,
        cache_creation_tokens=result.cache_creation_tokens,
        cache_enabled=cache_enabled,
    )
    return draft_text


def main() -> None:
    parser = argparse.ArgumentParser(description="섹션 초안 생성기")
    parser.add_argument("--brief", required=True, help="브리프 JSON 파일 경로")
    parser.add_argument("--section", required=True, help="작성할 섹션명")
    parser.add_argument("--sources", help="소스 번들 파일 경로 (선택)")
    parser.add_argument("--out", help="출력 마크다운 파일 경로 (생략 시 stdout)")
    parser.add_argument("--illustrate", action="store_true", help="본문 일러스트 placeholder/image hook 삽입")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 샘플 초안 생성")
    args = parser.parse_args()

    brief = json.loads(Path(args.brief).read_text(encoding="utf-8-sig"))
    source_bundle = Path(args.sources).read_text(encoding="utf-8-sig") if args.sources else ""
    draft = write_section(brief, args.section, source_bundle, dry_run=args.dry_run)
    if args.illustrate:
        try:
            from pipeline.illustration_hook import inject_illustrations
        except ModuleNotFoundError:
            from illustration_hook import inject_illustrations  # type: ignore

        out_path = Path(args.out) if args.out else None
        draft = inject_illustrations(
            draft,
            article_id=_derive_article_id(brief, args.section),
            skill="baoyu-article-illustrator",
            relative_to=out_path,
        )

    if args.out:
        Path(args.out).write_text(draft, encoding="utf-8")
        print(f"초안 저장 완료: {args.out}", file=sys.stderr)
        return

    if args.dry_run or args.illustrate:
        print(draft)


if __name__ == "__main__":
    main()
