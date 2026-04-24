from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline import illustration_hook
from pipeline.illustration_providers import IllustrationAuthError, IllustrationRateLimitError


class _FakeProvider:
    def __init__(self, provider: str, error: Exception | None = None) -> None:
        self.provider = provider
        self.error = error

    def generate(self, prompt, size, article_id, *, title, output_path, prompt_path=None):
        if self.error is not None:
            raise self.error
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        return type(
            "Result",
            (),
            {
                "image_path": output_path,
                "provider": self.provider,
                "model": self.provider,
                "request_id": f"{self.provider}-{article_id}",
                "license": f"{self.provider}-license",
                "cost_estimate": 0.0,
                "metadata": {},
            },
        )()


@pytest.mark.integration
def test_inject_illustrations_falls_through_rate_limit_then_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(illustration_hook, "ILLUSTRATION_ROOT", tmp_path / "output")
    monkeypatch.setattr(illustration_hook, "LOG_PATH", tmp_path / "logs" / "illustrations.jsonl")
    monkeypatch.setattr(illustration_hook, "DATA_DIR", tmp_path / "data")
    monkeypatch.setenv("CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER", "huggingface")
    monkeypatch.setattr(
        illustration_hook,
        "_build_provider",
        lambda name: {
            "huggingface": _FakeProvider("huggingface", IllustrationRateLimitError("rate")),
            "pollinations": _FakeProvider("pollinations"),
            "placeholder": _FakeProvider("placeholder"),
        }[name],
    )

    result = illustration_hook.inject_illustrations("## Section One\n\nBody", "art-1")
    assert 'data-rights="pollinations-license"' in result
    log_row = json.loads((tmp_path / "logs" / "illustrations.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert log_row["provider"] == "pollinations"
    assert log_row["provider_chain"] == ["huggingface", "pollinations", "placeholder"]


@pytest.mark.integration
def test_inject_illustrations_auth_error_short_circuits_to_placeholder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(illustration_hook, "ILLUSTRATION_ROOT", tmp_path / "output")
    monkeypatch.setattr(illustration_hook, "LOG_PATH", tmp_path / "logs" / "illustrations.jsonl")
    monkeypatch.setattr(illustration_hook, "DATA_DIR", tmp_path / "data")
    monkeypatch.setenv("CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER", "huggingface")
    monkeypatch.setattr(
        illustration_hook,
        "_build_provider",
        lambda name: {
            "huggingface": _FakeProvider("huggingface", IllustrationAuthError("auth")),
            "pollinations": _FakeProvider("pollinations"),
            "placeholder": _FakeProvider("placeholder"),
        }[name],
    )

    result = illustration_hook.inject_illustrations("## Section One\n\nBody", "art-2")
    assert 'data-rights="placeholder-for-review"' in result
