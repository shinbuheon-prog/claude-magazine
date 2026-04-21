"""
Langfuse observability helpers for pipeline modules.
"""
from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv()


def _build_langfuse_client() -> Any | None:
    try:
        from langfuse import Langfuse
    except ImportError:
        return None

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    if not public_key or not secret_key:
        return None

    try:
        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception:
        return None


_lf = _build_langfuse_client()
LANGFUSE_ENABLED = _lf is not None


def _compact_metadata(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value not in ("", None)}


def start_trace(
    name: str,
    model: str,
    topic: str = "",
    article_id: str = "",
    **metadata: Any,
) -> Any | None:
    """Create a Langfuse trace when enabled; otherwise return None."""
    if not LANGFUSE_ENABLED:
        return None

    trace_metadata = _compact_metadata(model=model, topic=topic, article_id=article_id, **metadata)
    try:
        return _lf.trace(name=name, metadata=trace_metadata)
    except Exception:
        return None


def trace_llm_call(name: str, model: str, topic: str = "", article_id: str = "") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that wraps an LLM call in a Langfuse trace.
    If Langfuse is unavailable, the wrapped function executes unchanged.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            trace = start_trace(name=name, model=model, topic=topic, article_id=article_id)
            if trace is not None and "langfuse_trace" not in kwargs:
                kwargs["langfuse_trace"] = trace
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_usage(
    trace_id: str | None,
    input_tokens: int,
    output_tokens: int,
    model: str,
    request_id: str | None = None,
) -> None:
    """Record token usage on a Langfuse trace when supported by the SDK."""
    if not LANGFUSE_ENABLED or not trace_id:
        return

    usage_payload = {
        "input": input_tokens,
        "output": output_tokens,
        "total": input_tokens + output_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }

    try:
        _lf.generation(
            trace_id=trace_id,
            name="anthropic_usage",
            model=model,
            usage=usage_payload,
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "request_id": request_id,
            },
        )
    except Exception:
        return

    try:
        _lf.flush()
    except Exception:
        return
