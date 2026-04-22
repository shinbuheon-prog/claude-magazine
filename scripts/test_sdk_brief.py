"""
brief_generator 프롬프트로 SDK 직접 호출 — 문제 지점 분리 테스트
"""
import asyncio
import os
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def test_case(name: str, system: str, user: str):
    print(f"\n--- {name} ---")
    print(f"system len: {len(system)}, user len: {len(user)}")
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions

        options = ClaudeAgentOptions(
            system_prompt=system,
            model="sonnet",
            max_turns=1,
        )

        result_text = ""
        msg_count = 0
        async for message in query(prompt=user, options=options):
            msg_count += 1
            if hasattr(message, "content") and isinstance(message.content, list):
                for block in message.content:
                    text = getattr(block, "text", None)
                    if text:
                        result_text += text

        print(f"  ✅ 성공 (msgs={msg_count}, text_len={len(result_text)})")
        if result_text:
            print(f"  응답: {result_text[:100]}...")
    except Exception as e:
        print(f"  ❌ 실패: {type(e).__name__}: {e}")


async def main():
    # 테스트 1: 짧은 한국어
    await test_case(
        "짧은 한국어",
        "당신은 편집자다.",
        "한 문장으로 답해라: 안녕하세요.",
    )

    # 테스트 2: brief_generator와 동일한 system prompt
    await test_case(
        "brief 시스템 프롬프트",
        (
            "당신은 한국어 B2B 기술 매체의 수석 편집자다.\n"
            "제공된 출처에만 근거하라.\n"
            "원문에 없는 주장, 수치, 인용은 만들지 말라.\n"
            "출력은 지정된 JSON만 반환하라."
        ),
        "한 문장으로 답해라: 테스트 중",
    )

    # 테스트 3: 실제 brief 템플릿 사용
    template_path = ROOT / "prompts" / "template_A_brief.txt"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
        user_prompt = template.replace("{{topic}}", "Claude 4 테스트").replace(
            "{{source_bundle}}", "(소스 없음)"
        )
        await test_case(
            "실제 brief 템플릿",
            "당신은 한국어 편집자다.",
            user_prompt,
        )


if __name__ == "__main__":
    asyncio.run(main())
