"""
팩트체크 에이전트
모델: claude-opus-4-7 (월간 딥리서치/최종 검토에만 사용)
사용법: python pipeline/fact_checker.py --draft drafts/article.md [--article-id ARTICLE_ID]
"""
import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
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

# Windows UTF-8 래핑 가드 — 다중 모듈 import 시 재래핑하면 closed file 에러 발생.
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


def load_template() -> str:
    tpl = PROMPTS_DIR / "template_C_factcheck.txt"
    return tpl.read_text(encoding="utf-8")


def load_sources_for_article(article_id: str | None) -> str:
    """출처 레지스트리에서 기사별 소스 묶음 조회 (TASK_004 완료 후 DB 연동)"""
    if not article_id:
        return "(출처 레지스트리 미연동 — 소스를 직접 붙여넣거나 TASK_004를 완료하세요)"

    try:
        from pipeline.source_registry import list_sources
        sources = list_sources(article_id)
        if not sources:
            return f"(article_id={article_id}에 등록된 소스가 없습니다)"
        parts = []
        for s in sources:
            parts.append(f"[{s['source_id']}] {s['publisher']} — {s['url']}")
        return "\n".join(parts)
    except ImportError:
        return "(source_registry 미구현 — TASK_004 완료 후 활성화됩니다)"


def run_factcheck(draft_text: str, source_bundle: str, category: str = "all") -> str:
    # TASK_033: provider 추상화 (CLAUDE_PROVIDER=sdk면 Max 구독 Opus 경유)
    try:
        from pipeline.claude_provider import get_provider
    except ModuleNotFoundError:
        from claude_provider import get_provider  # type: ignore

    provider = get_provider()
    template = load_template()
    heuristics_block = inject_heuristics(category)

    system_prompt = (
        "당신은 팩트체커다.\n"
        "초안의 각 문장을 출처와 대조해 아래 4개 중 하나로 판정하라.\n"
        "1) 확인됨\n2) 과장됨\n3) 출처 불충분\n4) 수정 필요"
    )
    if heuristics_block:
        system_prompt += "\n\n" + heuristics_block

    user_prompt = (
        template
        .replace("{{draft_text}}", draft_text)
        .replace("{{source_bundle}}", source_bundle)
    )

    trace = start_trace(name="fact_checking", model=f"opus-via-{provider.name}")

    # 스트리밍 콜백: 실시간 출력 (cp949 크래시 방지로 flush만)
    def _stream_print(chunk: str) -> None:
        try:
            print(chunk, end="", flush=True)
        except UnicodeEncodeError:
            pass  # Windows cp949 특수문자 실패 시 stdout은 skip, 최종 저장은 정상

    result = provider.stream_complete(
        system=system_prompt,
        user=user_prompt,
        model_tier="opus",
        max_tokens=8000,
        stream_callback=_stream_print,
    )

    print()
    result_text = result.text
    request_id = result.request_id
    input_tokens = result.input_tokens
    output_tokens = result.output_tokens

    log_usage(
        getattr(trace, "id", None),
        input_tokens,
        output_tokens,
        result.model or "claude-opus-4-7",
        request_id=request_id,
    )

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-opus-4-7",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    log_file = LOGS_DIR / f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} → {log_file.name}", file=sys.stderr)

    return result_text


def dry_run_preview(draft_text: str, source_bundle: str, category: str = "all") -> None:
    """API 호출 없이 시스템 프롬프트와 유저 프롬프트를 출력한다."""
    template = load_template()
    heuristics_block = inject_heuristics(category)

    system_prompt = (
        "당신은 팩트체커다.\n"
        "초안의 각 문장을 출처와 대조해 아래 4개 중 하나로 판정하라.\n"
        "1) 확인됨\n2) 과장됨\n3) 출처 불충분\n4) 수정 필요"
    )
    if heuristics_block:
        system_prompt += "\n\n" + heuristics_block

    user_prompt = (
        template
        .replace("{{draft_text}}", draft_text)
        .replace("{{source_bundle}}", source_bundle)
    )

    print("=" * 60)
    print("[DRY-RUN] SYSTEM PROMPT")
    print("=" * 60)
    print(system_prompt)
    print()
    print("=" * 60)
    print("[DRY-RUN] USER PROMPT")
    print("=" * 60)
    print(user_prompt)
    print()
    print("[DRY-RUN] API 호출 없이 종료합니다.")


def main():
    parser = argparse.ArgumentParser(description="팩트체크 에이전트")
    parser.add_argument("--draft", required=True, help="초안 마크다운 파일 경로")
    parser.add_argument("--article-id", help="출처 레지스트리 기사 ID (선택)")
    parser.add_argument("--category", default="all", help="editor heuristics category")
    parser.add_argument("--out", help="결과 저장 경로 (생략 시 자동 생성)")
    parser.add_argument("--dry-run", action="store_true",
                        help="API 호출 없이 시스템/유저 프롬프트를 미리보기 출력")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8")
    source_bundle = load_sources_for_article(args.article_id)

    if args.dry_run:
        dry_run_preview(draft_text, source_bundle, category=args.category)
        return

    print("=== 팩트체크 시작 ===", file=sys.stderr)
    result = run_factcheck(draft_text, source_bundle, category=args.category)

    out_path = args.out or str(LOGS_DIR / f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    Path(out_path).write_text(result, encoding="utf-8")
    print(f"\n[완료] 팩트체크 결과 저장: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
