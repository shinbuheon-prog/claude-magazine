"""
Claude Agent SDK 기본 동작 확인 (TASK_033 Step 1a)
SDK의 메시지 구조·스트리밍·usage·session id 등을 파악하기 위한 최소 스크립트.
"""
import asyncio
import sys
from pathlib import Path

# Windows UTF-8
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main():
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError as e:
        print(f"❌ SDK import 실패: {e}")
        return 1

    print("=== Claude Agent SDK 기본 테스트 ===\n")
    print("[1/3] SDK import OK\n")

    # 간단한 Sonnet 호출
    print("[2/3] Sonnet 호출 테스트")
    options = ClaudeAgentOptions(
        system_prompt="당신은 간결하게 답하는 편집 보조 AI입니다.",
        model="sonnet",
        max_turns=1,
    )

    prompt = "안녕하세요. '테스트 성공'이라는 한 문장만 응답해주세요."

    message_types_seen = []
    result_text = ""
    usage_info = None
    session_id = None

    try:
        async for message in query(prompt=prompt, options=options):
            msg_type = type(message).__name__
            message_types_seen.append(msg_type)

            # 모든 속성 찾아보기
            if hasattr(message, "content"):
                content = message.content
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "text"):
                            result_text += block.text
                        elif hasattr(block, "type"):
                            print(f"   block type: {block.type}")

            if hasattr(message, "usage") and message.usage:
                usage_info = message.usage

            if hasattr(message, "session_id"):
                session_id = message.session_id

    except Exception as e:
        print(f"❌ 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print(f"\n[3/3] 결과 분석")
    print(f"   메시지 타입들: {message_types_seen}")
    print(f"   응답 텍스트: {result_text[:200]}")
    print(f"   usage: {usage_info}")
    print(f"   session_id: {session_id}")

    if result_text:
        print("\n✅ 기본 호출 성공")
        return 0
    else:
        print("\n⚠️ 응답 텍스트 없음")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
