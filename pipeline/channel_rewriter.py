"""
채널별 재가공기 (SNS·이메일 요약)
모델: claude-haiku-4-5 (저비용 고속)
사용법: python pipeline/channel_rewriter.py --draft drafts/article.md --channel sns
"""
import argparse
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

load_dotenv()

ROOT = Path(__file__).parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

CHANNEL_INSTRUCTIONS = {
    "sns": (
        "트위터/X 스레드 형식으로 재가공하라.\n"
        "첫 트윗은 후킹 문장 + 핵심 수치.\n"
        "이어지는 트윗은 2~3개, 각 280자 이내.\n"
        "마지막 트윗은 CTA (원문 링크 자리 표시).\n"
        "해시태그 2~3개 포함."
    ),
    "email": (
        "주간 뉴스레터 요약 섹션으로 재가공하라.\n"
        "제목(이메일 subject line), 리드 문장, 핵심 포인트 3개, 원문 링크 안내.\n"
        "총 150단어 이내."
    ),
    "linkedin": (
        "LinkedIn 포스트로 재가공하라.\n"
        "첫 2줄이 핵심 인사이트 (스크롤 없이 보임).\n"
        "본문 5~7줄, 비즈니스 독자 대상 톤.\n"
        "해시태그 3~5개."
    ),
}


def rewrite_for_channel(draft_text: str, channel: str) -> str:
    if channel not in CHANNEL_INSTRUCTIONS:
        raise ValueError(f"지원하지 않는 채널: {channel}. 지원: {list(CHANNEL_INSTRUCTIONS.keys())}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system_prompt = (
        "당신은 SNS·이메일 콘텐츠 전문가다.\n"
        "한국어로 작성하고, 마케팅 문구와 과장은 금지한다.\n"
        "원문의 핵심 사실만 유지하고, 링크·출처를 항상 포함한다."
    )

    user_prompt = (
        f"다음 기사 초안을 {channel} 형식으로 재가공하라.\n\n"
        f"<instructions>\n{CHANNEL_INSTRUCTIONS[channel]}\n</instructions>\n\n"
        f"<draft>\n{draft_text}\n</draft>"
    )

    result_text = ""
    request_id = None
    input_tokens = 0
    output_tokens = 0
    trace = start_trace(name="channel_rewriting", model="claude-haiku-4-5-20251001")

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text
            print(text, end="", flush=True)
        final = stream.get_final_message()
        request_id = getattr(final, "_request_id", None)
        input_tokens = final.usage.input_tokens
        output_tokens = final.usage.output_tokens

    print()
    log_usage(
        getattr(trace, "id", None),
        input_tokens,
        output_tokens,
        "claude-haiku-4-5-20251001",
        request_id=request_id,
    )

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-haiku-4-5-20251001",
        "channel": channel,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    log_file = LOGS_DIR / f"rewrite_{channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} → {log_file.name}", file=sys.stderr)

    return result_text


def main():
    parser = argparse.ArgumentParser(description="채널별 재가공기")
    parser.add_argument("--draft", required=True, help="초안 마크다운 파일 경로")
    parser.add_argument("--channel", required=True, choices=list(CHANNEL_INSTRUCTIONS.keys()))
    parser.add_argument("--out", help="출력 파일 경로 (생략 시 stdout)")
    args = parser.parse_args()

    draft_text = Path(args.draft).read_text(encoding="utf-8")
    result = rewrite_for_channel(draft_text, args.channel)

    if args.out:
        Path(args.out).write_text(result, encoding="utf-8")
        print(f"\n저장 완료: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
