"""
섹션 초안 생성기
모델: claude-sonnet-4-6, effort=medium
사용법: python pipeline/draft_writer.py --brief brief.json --section "섹션명"
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
PROMPTS_DIR = ROOT / "prompts"
DRAFTS_DIR = ROOT / "drafts"
LOGS_DIR = ROOT / "logs"
DRAFTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def load_template() -> str:
    tpl = PROMPTS_DIR / "template_B_draft.txt"
    return tpl.read_text(encoding="utf-8")


def write_section(brief: dict, section_name: str, source_bundle: str = "") -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = load_template()

    system_prompt = (
        "당신은 신중한 기술 저널리스트다.\n"
        "한국어로만 작성하라.\n"
        "각 문단은 하나의 결론만 다룬다.\n"
        "출처 없는 단정은 금지한다."
    )

    user_prompt = (
        template
        .replace("{{approved_brief}}", json.dumps(brief, ensure_ascii=False, indent=2))
        .replace("{{section_name}}", section_name)
        .replace("{{source_bundle}}", source_bundle or "(소스 묶음 없음)")
    )

    draft_text = ""
    request_id = None

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            draft_text += text
            print(text, end="", flush=True)
        final = stream.get_final_message()
        request_id = getattr(final, "_request_id", None)

    print()  # 줄바꿈

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-sonnet-4-6",
        "section": section_name,
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
    }
    log_file = LOGS_DIR / f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} → {log_file.name}", file=sys.stderr)

    return draft_text


def main():
    parser = argparse.ArgumentParser(description="섹션 초안 생성기")
    parser.add_argument("--brief", required=True, help="브리프 JSON 파일 경로")
    parser.add_argument("--section", required=True, help="작성할 섹션명")
    parser.add_argument("--sources", help="소스 번들 파일 경로 (선택)")
    parser.add_argument("--out", help="출력 마크다운 파일 경로 (생략 시 stdout)")
    args = parser.parse_args()

    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    source_bundle = Path(args.sources).read_text(encoding="utf-8") if args.sources else ""

    draft = write_section(brief, args.section, source_bundle)

    if args.out:
        Path(args.out).write_text(draft, encoding="utf-8")
        print(f"\n초안 저장 완료: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
