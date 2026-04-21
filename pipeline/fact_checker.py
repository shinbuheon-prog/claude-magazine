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

# Windows 환경에서 한국어/특수문자 출력을 위한 UTF-8 강제 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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


def run_factcheck(draft_text: str, source_bundle: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = load_template()

    system_prompt = (
        "당신은 팩트체커다.\n"
        "초안의 각 문장을 출처와 대조해 아래 4개 중 하나로 판정하라.\n"
        "1) 확인됨\n2) 과장됨\n3) 출처 불충분\n4) 수정 필요"
    )

    user_prompt = (
        template
        .replace("{{draft_text}}", draft_text)
        .replace("{{source_bundle}}", source_bundle)
    )

    result_text = ""
    request_id = None

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text
            print(text, end="", flush=True)
        final = stream.get_final_message()
        request_id = getattr(final, "_request_id", None)

    print()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-opus-4-7",
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
    }
    log_file = LOGS_DIR / f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} → {log_file.name}", file=sys.stderr)

    return result_text


def dry_run_preview(draft_text: str, source_bundle: str) -> None:
    """API 호출 없이 시스템 프롬프트와 유저 프롬프트를 출력한다."""
    template = load_template()

    system_prompt = (
        "당신은 팩트체커다.\n"
        "초안의 각 문장을 출처와 대조해 아래 4개 중 하나로 판정하라.\n"
        "1) 확인됨\n2) 과장됨\n3) 출처 불충분\n4) 수정 필요"
    )

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
    parser.add_argument("--out", help="결과 저장 경로 (생략 시 자동 생성)")
    parser.add_argument("--dry-run", action="store_true",
                        help="API 호출 없이 시스템/유저 프롬프트를 미리보기 출력")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8")
    source_bundle = load_sources_for_article(args.article_id)

    if args.dry_run:
        dry_run_preview(draft_text, source_bundle)
        return

    print("=== 팩트체크 시작 ===", file=sys.stderr)
    result = run_factcheck(draft_text, source_bundle)

    out_path = args.out or str(LOGS_DIR / f"factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    Path(out_path).write_text(result, encoding="utf-8")
    print(f"\n[완료] 팩트체크 결과 저장: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
