"""
기사 브리프 생성기
모델: claude-sonnet-4-6, effort=medium
사용법: python pipeline/brief_generator.py --topic "TOPIC" [--sources src1.md src2.md]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
PROMPTS_DIR = ROOT / "prompts"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

BRIEF_SCHEMA = {
    "working_title": "string",
    "angle": "string",
    "why_now": "string",
    "outline": [{"section": "string", "points": ["string"]}],
    "evidence_map": [{"claim": "string", "source_id": "string"}],
    "unknowns": ["string"],
    "risk_flags": ["string"],
}


def load_template() -> str:
    tpl = PROMPTS_DIR / "template_A_brief.txt"
    return tpl.read_text(encoding="utf-8")


def load_sources(source_paths: list[str]) -> str:
    if not source_paths:
        return "(소스 없음 — 웹 검색 결과나 직접 입력한 텍스트를 여기에 붙여넣으세요)"
    parts = []
    for path in source_paths:
        p = Path(path)
        if p.exists():
            parts.append(f"=== {p.name} ===\n{p.read_text(encoding='utf-8')}")
        else:
            parts.append(f"=== {path} ===\n(파일을 찾을 수 없음)")
    return "\n\n".join(parts)


def generate_brief(topic: str, source_bundle: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = load_template()

    system_prompt = (
        "당신은 한국어 B2B 기술 매체의 수석 편집자다.\n"
        "제공된 출처에만 근거하라.\n"
        "원문에 없는 주장, 수치, 인용은 만들지 말라.\n"
        "출력은 지정된 JSON만 반환하라."
    )

    user_prompt = template.replace("{{topic}}", topic).replace(
        "{{source_bundle}}", source_bundle
    )

    result_text = ""
    request_id = None

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text
        final = stream.get_final_message()
        request_id = getattr(final, "_request_id", None)

    # JSON 추출
    json_start = result_text.find("{")
    json_end = result_text.rfind("}") + 1
    brief_json = json.loads(result_text[json_start:json_end])

    # 로그 저장
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-sonnet-4-6",
        "topic": topic,
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
    }
    log_file = LOGS_DIR / f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} → {log_file.name}", file=sys.stderr)

    return brief_json


def main():
    parser = argparse.ArgumentParser(description="기사 브리프 생성기")
    parser.add_argument("--topic", required=True, help="기사 주제")
    parser.add_argument("--sources", nargs="*", default=[], help="소스 파일 경로들")
    parser.add_argument("--out", help="출력 JSON 파일 경로 (생략 시 stdout)")
    args = parser.parse_args()

    source_bundle = load_sources(args.sources)
    brief = generate_brief(args.topic, source_bundle)

    output = json.dumps(brief, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"브리프 저장 완료: {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
