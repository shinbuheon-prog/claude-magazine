"""
Claude provider abstraction.

This module keeps the existing three execution paths:
- `api`: Anthropic Messages API
- `sdk`: Claude Agent SDK
- `mock`: local fixed response for tests

TASK_044 adds:
- block-based message execution for prompt caching
- token counting helper

TASK_045 uses the same block-based API path for Citations.
"""
from __future__ import annotations

import asyncio
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

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
    text: str
    request_id: str | None = None
    session_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    model: str = ""
    provider: str = ""
    raw: Any = None


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")

    texts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text" and block.get("text"):
                texts.append(str(block["text"]))
            elif block.get("type") == "document":
                title = str(block.get("title") or "Document")
                source = block.get("source") or {}
                if isinstance(source, dict):
                    if source.get("type") == "text":
                        texts.append(f"[{title}]\n{source.get('data', '')}")
                    elif source.get("type") == "content":
                        parts = []
                        for item in source.get("content", []):
                            if isinstance(item, dict) and item.get("type") == "text":
                                parts.append(str(item.get("text") or ""))
                        texts.append(f"[{title}]\n" + "\n".join(parts))
        else:
            text = getattr(block, "text", None)
            if text:
                texts.append(str(text))
    return "\n\n".join(part for part in texts if part)


class Provider(ABC):
    name: str = "abstract"

    @abstractmethod
    def stream_complete(
        self,
        system: str,
        user: str,
        model_tier: str = "sonnet",
        max_tokens: int = 4096,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        """Backward-compatible simple text path."""

    def complete_with_blocks(
        self,
        *,
        system_blocks: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        model_tier: str = "sonnet",
        max_tokens: int = 4096,
        stream: bool = False,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        system_text = _extract_text_from_content(system_blocks or [])
        user_parts = []
        for message in messages or []:
            user_parts.append(_extract_text_from_content(message.get("content", "")))
        user_text = "\n\n".join(part for part in user_parts if part)
        return self.stream_complete(
            system=system_text,
            user=user_text,
            model_tier=model_tier,
            max_tokens=max_tokens,
            stream_callback=stream_callback if stream else None,
        )

    def count_tokens(
        self,
        *,
        system_blocks: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        model_tier: str = "sonnet",
    ) -> int:
        text = _extract_text_from_content(system_blocks or [])
        for message in messages or []:
            text += "\n" + _extract_text_from_content(message.get("content", ""))
        return max(1, len(text) // 4)


class AnthropicAPIProvider(Provider):
    name = "api"

    def __init__(self) -> None:
        import anthropic as _anthropic_mod

        self._anthropic_mod = _anthropic_mod

    def _client(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        client_cls = getattr(self._anthropic_mod, "Anthropic")
        return client_cls(api_key=api_key)

    @staticmethod
    def _usage_value(usage: Any, key: str) -> int:
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(key, 0) or 0)
        return int(getattr(usage, key, 0) or 0)

    @staticmethod
    def _text_from_response(response: Any) -> str:
        chunks: list[str] = []
        for block in getattr(response, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                chunks.append(str(text))
        return "".join(chunks)

    def stream_complete(
        self,
        system: str,
        user: str,
        model_tier: str = "sonnet",
        max_tokens: int = 4096,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        system_blocks = [{"type": "text", "text": system}]
        messages = [{"role": "user", "content": [{"type": "text", "text": user}]}]
        return self.complete_with_blocks(
            system_blocks=system_blocks,
            messages=messages,
            model_tier=model_tier,
            max_tokens=max_tokens,
            stream=True,
            stream_callback=stream_callback,
        )

    def complete_with_blocks(
        self,
        *,
        system_blocks: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        model_tier: str = "sonnet",
        max_tokens: int = 4096,
        stream: bool = False,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        client = self._client()
        model = MODEL_ALIASES["api"][model_tier]
        system_payload: str | list[dict[str, Any]]
        system_payload = system_blocks or ""
        messages_payload = messages or []

        if stream:
            result_text = ""
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system_payload,
                messages=messages_payload,
            ) as stream_obj:
                for chunk in stream_obj.text_stream:
                    result_text += chunk
                    if stream_callback:
                        stream_callback(chunk)
                final = stream_obj.get_final_message()
            usage = getattr(final, "usage", None)
            return CompleteResult(
                text=result_text,
                request_id=getattr(final, "id", None) or getattr(final, "_request_id", None),
                input_tokens=self._usage_value(usage, "input_tokens"),
                output_tokens=self._usage_value(usage, "output_tokens"),
                cache_read_tokens=self._usage_value(usage, "cache_read_input_tokens"),
                cache_creation_tokens=self._usage_value(usage, "cache_creation_input_tokens"),
                model=model,
                provider=self.name,
                raw=final,
            )

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_payload,
            messages=messages_payload,
        )
        usage = getattr(response, "usage", None)
        return CompleteResult(
            text=self._text_from_response(response),
            request_id=getattr(response, "id", None) or getattr(response, "_request_id", None),
            input_tokens=self._usage_value(usage, "input_tokens"),
            output_tokens=self._usage_value(usage, "output_tokens"),
            cache_read_tokens=self._usage_value(usage, "cache_read_input_tokens"),
            cache_creation_tokens=self._usage_value(usage, "cache_creation_input_tokens"),
            model=model,
            provider=self.name,
            raw=response,
        )

    def count_tokens(
        self,
        *,
        system_blocks: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        model_tier: str = "sonnet",
    ) -> int:
        client = self._client()
        model = MODEL_ALIASES["api"][model_tier]
        response = client.messages.count_tokens(
            model=model,
            system=system_blocks or "",
            messages=messages or [],
        )
        if hasattr(response, "input_tokens"):
            return int(response.input_tokens)
        if isinstance(response, dict):
            return int(response.get("input_tokens", 0) or 0)
        return super().count_tokens(system_blocks=system_blocks, messages=messages, model_tier=model_tier)


class ClaudeAgentSDKProvider(Provider):
    name = "sdk"

    def __init__(self) -> None:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, query
        except ImportError as exc:
            raise RuntimeError("claude-agent-sdk is not installed") from exc

        self._query = query
        self._Options = ClaudeAgentOptions

    def stream_complete(
        self,
        system: str,
        user: str,
        model_tier: str = "sonnet",
        max_tokens: int = 4096,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        model = MODEL_ALIASES["sdk"][model_tier]
        return asyncio.run(self._async_stream(system, user, model, stream_callback))

    async def _async_stream(
        self,
        system: str,
        user: str,
        model: str,
        stream_callback: Callable[[str], None] | None,
    ) -> CompleteResult:
        options = self._Options(system_prompt=system, model=model, max_turns=1)

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
                if msg_type == "AssistantMessage" and hasattr(message, "content"):
                    content = message.content
                    if isinstance(content, list):
                        for block in content:
                            text = getattr(block, "text", None)
                            if text:
                                result_text += text
                                if stream_callback:
                                    stream_callback(text)
                if msg_type == "ResultMessage":
                    if hasattr(message, "session_id"):
                        session_id = message.session_id
                    usage = getattr(message, "usage", None)
                    if isinstance(usage, dict):
                        input_tokens = int(usage.get("input_tokens", 0) or 0)
                        output_tokens = int(usage.get("output_tokens", 0) or 0)
                        cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
                        cache_creation = int(usage.get("cache_creation_input_tokens", 0) or 0)
                    elif usage is not None:
                        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
                        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        except Exception as exc:
            import traceback

            print("[debug] SDK traceback:", file=sys.stderr)
            traceback.print_exc()
            raise RuntimeError(f"Claude Agent SDK call failed: {type(exc).__name__}: {exc}") from exc

        return CompleteResult(
            text=result_text,
            request_id=session_id,
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            model=model,
            provider=self.name,
            raw=raw_messages if len(raw_messages) < 20 else None,
        )


class MockProvider(Provider):
    name = "mock"

    def __init__(
        self,
        response_text: str = (
            '{"working_title": "mock", "angle": "mock", "why_now": "mock", '
            '"outline": [], "evidence_map": [], "unknowns": [], "risk_flags": []}'
        ),
    ) -> None:
        self._response = response_text

    def stream_complete(
        self,
        system: str,
        user: str,
        model_tier: str = "sonnet",
        max_tokens: int = 4096,
        stream_callback: Callable[[str], None] | None = None,
    ) -> CompleteResult:
        if stream_callback:
            for chunk in self._response[:100]:
                stream_callback(chunk)
        return CompleteResult(
            text=self._response,
            request_id=f"mock-{model_tier}-req",
            input_tokens=10,
            output_tokens=max(1, len(self._response) // 4),
            model=f"mock-{model_tier}",
            provider=self.name,
        )


_provider_cache: Provider | None = None


def get_provider(override: str | None = None, refresh: bool = False) -> Provider:
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
        raise ValueError(f"Unsupported CLAUDE_PROVIDER: {kind} (api|sdk|mock)")
    return _provider_cache


def _smoke_test() -> int:
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== claude_provider smoke test ===\n")
    checks: list[tuple[str, bool]] = []

    try:
        mock = get_provider(override="mock", refresh=True)
        result = mock.stream_complete(system="test", user="test")
        checks.append(("Mock provider", bool(result.text)))
    except Exception as exc:
        checks.append((f"Mock provider error: {exc}", False))

    try:
        if os.environ.get("ANTHROPIC_API_KEY"):
            api = get_provider(override="api", refresh=True)
            count = api.count_tokens(
                system_blocks=[{"type": "text", "text": "system"}],
                messages=[{"role": "user", "content": [{"type": "text", "text": "user"}]}],
            )
            checks.append(("API provider count_tokens", count > 0))
        else:
            checks.append(("API provider skipped (no key)", True))
    except Exception as exc:
        checks.append((f"API provider error: {exc}", False))

    try:
        sdk = get_provider(override="sdk", refresh=True)
        checks.append(("SDK provider instance", isinstance(sdk, ClaudeAgentSDKProvider)))
    except Exception as exc:
        checks.append((f"SDK provider error: {exc}", False))

    passed = sum(1 for _, ok in checks if ok)
    for idx, (name, ok) in enumerate(checks, start=1):
        status = "OK" if ok else "FAIL"
        print(f"[{idx}/{len(checks)}] {status} {name}")

    print(f"\n=== Result: {passed}/{len(checks)} passed ===")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(_smoke_test())
