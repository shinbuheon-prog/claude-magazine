"""
Claude Provider 추상화 (TASK_033)

파이프라인 모듈이 Claude API를 호출하는 방식을 추상화.
- AnthropicAPIProvider: 기존 anthropic 라이브러리 (pay-per-use)
- ClaudeAgentSDKProvider: Claude Agent SDK (Pro/Max 구독 내 동작, 추가 비용 0)
- MockProvider: 테스트용 고정 응답

환경변수:
    CLAUDE_PROVIDER=sdk  # sdk | api | mock  (기본: api, 하위 호환)

모델 티어 매핑:
    "sonnet" → claude-sonnet-4-6 / "sonnet" (SDK)
    "opus"   → claude-opus-4-7   / "opus" (SDK)
    "haiku"  → claude-haiku-4-5-20251001 / "haiku" (SDK)
"""
from __future__ import annotations

import asyncio
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

# ── 모델 티어 매핑 ────────────────────────────────

MODEL_ALIASES = {
    "api": {
        "sonnet": "claude-sonnet-4-6",
        "opus": "claude-opus-4-7",
        "haiku": "claude-haiku-4-5-20251001",
    },
    "sdk": {
        "sonnet": "sonnet",
        "opus": "opus",
        "haiku": "haiku",
    },
}


@dataclass
class CompleteResult:
    """Provider 호출 결과 공통 인터페이스."""
    text: str
    request_id: str | None = None
    session_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    model: str = ""
    provider: str = ""
    raw: Any = None  # 원본 응답 (디버그용)


# ── Provider 인터페이스 ──────────────────────────

class Provider(ABC):
    """Claude 호출 공통 인터페이스."""
    name: str = "abstract"

    @abstractmethod
    def stream_complete(
        self,
        system: str,
        user: str,
        model_tier: str = "sonnet",  # sonnet | opus | haiku
        max_tokens: int = 4096,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        """동기식 스트리밍 완료. chunk 단위로 stream_callback 호출."""


# ── AnthropicAPI (기존 경로) ──────────────────────

class AnthropicAPIProvider(Provider):
    name = "api"

    def __init__(self):
        # 초기화 시점에 모듈만 확보, 클래스 참조는 호출마다 동적으로 가져와
        # 기존 test_e2e.py 등의 anthropic.Anthropic patch 가 정상 동작하도록 한다.
        import anthropic as _anthropic_mod
        self._anthropic_mod = _anthropic_mod

    def stream_complete(self, system, user, model_tier="sonnet", max_tokens=4096, stream_callback=None):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경변수 미설정")

        # 동적 참조 — patch 된 Anthropic 클래스도 반영됨
        client_cls = getattr(self._anthropic_mod, "Anthropic")
        client = client_cls(api_key=api_key)
        model = MODEL_ALIASES["api"][model_tier]

        result_text = ""
        request_id = None
        input_tokens = 0
        output_tokens = 0

        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for chunk in stream.text_stream:
                result_text += chunk
                if stream_callback:
                    stream_callback(chunk)
            final = stream.get_final_message()
            request_id = getattr(final, "_request_id", None)
            if hasattr(final, "usage"):
                input_tokens = final.usage.input_tokens
                output_tokens = final.usage.output_tokens

        return CompleteResult(
            text=result_text,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            provider=self.name,
        )


# ── ClaudeAgentSDK (Max 구독 경유) ────────────────

class ClaudeAgentSDKProvider(Provider):
    name = "sdk"

    def __init__(self):
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
            self._query = query
            self._Options = ClaudeAgentOptions
        except ImportError as exc:
            raise RuntimeError(
                "claude-agent-sdk 미설치 — `pip install claude-agent-sdk`"
            ) from exc

    def stream_complete(self, system, user, model_tier="sonnet", max_tokens=4096, stream_callback=None):
        model = MODEL_ALIASES["sdk"][model_tier]
        return asyncio.run(
            self._async_stream(system, user, model, max_tokens, stream_callback)
        )

    async def _async_stream(self, system, user, model, max_tokens, stream_callback):
        options = self._Options(
            system_prompt=system,
            model=model,
            max_turns=1,
        )

        result_text = ""
        session_id = None
        input_tokens = 0
        output_tokens = 0
        cache_read = 0
        cache_creation = 0
        raw_messages: list[Any] = []

        try:
            async for message in self._query(prompt=user, options=options):
                raw_messages.append(message)
                msg_type = type(message).__name__

                # AssistantMessage: 실제 응답 텍스트
                if msg_type == "AssistantMessage" and hasattr(message, "content"):
                    content = message.content
                    if isinstance(content, list):
                        for block in content:
                            text = getattr(block, "text", None)
                            if text:
                                result_text += text
                                if stream_callback:
                                    stream_callback(text)

                # ResultMessage: usage + session_id
                if msg_type == "ResultMessage":
                    if hasattr(message, "session_id"):
                        session_id = message.session_id
                    usage = getattr(message, "usage", None)
                    if usage:
                        # usage는 dict 형태일 수 있음
                        if isinstance(usage, dict):
                            input_tokens = usage.get("input_tokens", 0) or 0
                            output_tokens = usage.get("output_tokens", 0) or 0
                            cache_read = usage.get("cache_read_input_tokens", 0) or 0
                            cache_creation = usage.get("cache_creation_input_tokens", 0) or 0
                        else:
                            input_tokens = getattr(usage, "input_tokens", 0) or 0
                            output_tokens = getattr(usage, "output_tokens", 0) or 0
        except Exception as exc:
            # SDK 실패 시 상세 정보 포함해 예외 전파
            import traceback
            print("[debug] SDK traceback:", file=sys.stderr)
            traceback.print_exc()
            raise RuntimeError(f"Claude Agent SDK 호출 실패: {type(exc).__name__}: {exc}") from exc

        return CompleteResult(
            text=result_text,
            request_id=session_id,  # SDK는 별도 request_id 없어 session_id로 대체
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            model=model,
            provider=self.name,
            raw=raw_messages if len(raw_messages) < 20 else None,
        )


# ── Mock (테스트용) ──────────────────────────────

class MockProvider(Provider):
    name = "mock"

    def __init__(self, response_text: str = '{"working_title": "mock", "angle": "mock", "why_now": "mock", "outline": [], "evidence_map": [], "unknowns": [], "risk_flags": []}'):
        self._response = response_text

    def stream_complete(self, system, user, model_tier="sonnet", max_tokens=4096, stream_callback=None):
        # 청크 단위로 전달
        if stream_callback:
            for chunk in self._response[:100]:  # 일부만 스트리밍
                stream_callback(chunk)

        return CompleteResult(
            text=self._response,
            request_id=f"mock-{model_tier}-req",
            input_tokens=10,
            output_tokens=len(self._response) // 4,
            model=f"mock-{model_tier}",
            provider=self.name,
        )


# ── Factory ──────────────────────────────────────

_provider_cache: Provider | None = None


def get_provider(override: str | None = None, refresh: bool = False) -> Provider:
    """
    환경변수 CLAUDE_PROVIDER에 따라 Provider 반환.
    - "api" (기본): AnthropicAPIProvider
    - "sdk": ClaudeAgentSDKProvider
    - "mock": MockProvider
    """
    global _provider_cache

    kind = (override or os.environ.get("CLAUDE_PROVIDER", "api")).lower()

    if _provider_cache is not None and _provider_cache.name == kind and not refresh:
        return _provider_cache

    if kind == "sdk":
        _provider_cache = ClaudeAgentSDKProvider()
    elif kind == "mock":
        _provider_cache = MockProvider()
    elif kind == "api":
        _provider_cache = AnthropicAPIProvider()
    else:
        raise ValueError(f"알 수 없는 CLAUDE_PROVIDER: {kind} (api|sdk|mock 중 선택)")

    return _provider_cache


# ── 스모크 테스트 ─────────────────────────────────

def _smoke_test() -> int:
    """provider 3종 인스턴스 생성 테스트 (실제 호출 없음)."""
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== claude_provider 스모크 테스트 ===\n")

    checks = []

    # 1. Mock provider
    try:
        mock = get_provider(override="mock", refresh=True)
        result = mock.stream_complete(
            system="test system",
            user="test user",
            model_tier="sonnet",
            max_tokens=100,
        )
        checks.append(("Mock provider", bool(result.text)))
    except Exception as e:
        checks.append((f"Mock provider — ERROR: {e}", False))

    # 2. API provider (인스턴스만, 호출은 안 함)
    try:
        if os.environ.get("ANTHROPIC_API_KEY"):
            api = get_provider(override="api", refresh=True)
            checks.append(("API provider 인스턴스", isinstance(api, AnthropicAPIProvider)))
        else:
            checks.append(("API provider — SKIP (no API key)", True))
    except Exception as e:
        checks.append((f"API provider — ERROR: {e}", False))

    # 3. SDK provider (인스턴스만)
    try:
        sdk = get_provider(override="sdk", refresh=True)
        checks.append(("SDK provider 인스턴스", isinstance(sdk, ClaudeAgentSDKProvider)))
    except Exception as e:
        checks.append((f"SDK provider — ERROR: {e}", False))

    passed = sum(1 for _, ok in checks if ok)
    for idx, (name, ok) in enumerate(checks, 1):
        status = "✅" if ok else "❌"
        print(f"[{idx}/{len(checks)}] {status} {name}")

    print(f"\n=== 결과: {passed}/{len(checks)} 통과 ===")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(_smoke_test())
