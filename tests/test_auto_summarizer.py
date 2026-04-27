from __future__ import annotations

import json
from pathlib import Path

from pipeline import auto_summarizer, source_registry


class FakeProvider:
    def __init__(self):
        self.calls = []

    def count_tokens(self, **kwargs):
        return 42

    def stream_complete(self, system, user, model_tier="sonnet", max_tokens=0, stream_callback=None):
        self.calls.append((model_tier, user))
        if model_tier == "haiku":
            text = "A short Korean one-line summary under fifty chars"
        elif "JSON list" in user:
            text = json.dumps(
                [
                    {"quote": "q" * 250, "context": "ctx", "page_or_section": "sec"},
                ],
                ensure_ascii=False,
            )
        else:
            text = "line1\nline2\nline3\nline4"
        return type(
            "Result",
            (),
            {
                "text": text,
                "request_id": f"req-{model_tier}",
                "model": f"mock-{model_tier}",
                "provider": "mock",
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_tokens": 0,
            },
        )()


class NoDryRunProvider:
    def count_tokens(self, **kwargs):
        raise AssertionError("dry-run should not call provider.count_tokens")

    def stream_complete(self, *args, **kwargs):
        raise AssertionError("dry-run should not call provider.stream_complete")


def _setup_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "source_registry.db"
    logs_dir = tmp_path / "logs"
    monkeypatch.setattr(source_registry, "DB_PATH", db_path)
    monkeypatch.setattr(auto_summarizer, "DB_PATH", db_path)
    monkeypatch.setattr(auto_summarizer, "LOGS_DIR", logs_dir)
    source_registry.init_db()
    return source_registry.add_source(
        url="https://example.com/a",
        title="Claude on AWS",
        publisher="Example",
        content_preview="preview",
        content_body="Body text " * 50,
        rights_status="unknown",
        topics=["claude", "aws"],
    )


def test_oneliner_haiku_returns_50char_max(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    result = auto_summarizer.summarize_source(source_id, levels=("oneliner",))
    assert len(result["summary_oneliner"]) <= 50


def test_3line_sonnet_format(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    result = auto_summarizer.summarize_source(source_id, levels=("3line",))
    assert len(result["summary_3line"].splitlines()) == 3


def test_quotes_truncate_200char(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    result = auto_summarizer.summarize_source(source_id, levels=("quotes",))
    assert len(result["key_quotes"][0]["quote"]) <= 203


def test_request_id_saved_to_logs(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    logs_dir = tmp_path / "logs"
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    auto_summarizer.summarize_source(source_id, levels=("oneliner",))
    payload = json.loads(next(logs_dir.glob("auto_summarizer_*.json")).read_text(encoding="utf-8"))
    assert payload[0]["request_id"] == "req-haiku"


def test_schema_migration_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "source_registry.db"
    monkeypatch.setattr(source_registry, "DB_PATH", db_path)
    source_registry.init_db()
    source_registry.init_db()
    assert db_path.exists()


def test_batch_summarize_skips_already_done(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    auto_summarizer.summarize_source(source_id, levels=("oneliner",))
    results = auto_summarizer.batch_summarize_pending(max_count=10)
    assert results == []


def test_quote_limit_from_source_respected(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    source_registry.update_source(source_id, rights_status="free", quote_limit=100)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    result = auto_summarizer.summarize_source(source_id, levels=("quotes",))
    assert len(result["key_quotes"][0]["quote"]) <= 103


def test_batch_levels_respected(tmp_path, monkeypatch):
    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    results = auto_summarizer.batch_summarize_pending(max_count=10, levels=("oneliner",))
    assert len(results) == 1
    assert results[0]["summary_oneliner"]
    assert results[0]["summary_3line"] == ""
    assert results[0]["key_quotes"] == []


def test_dry_run_skips_provider_calls(tmp_path, monkeypatch):
    source_id = _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: NoDryRunProvider())
    result = auto_summarizer.summarize_source(source_id, levels=("oneliner", "quotes"), dry_run=True)
    assert result["total_tokens"] > 0
    assert result["summary_oneliner"] == ""


def test_korean_utf8_safe(tmp_path, monkeypatch):
    db_path = tmp_path / "source_registry.db"
    monkeypatch.setattr(source_registry, "DB_PATH", db_path)
    monkeypatch.setattr(auto_summarizer, "DB_PATH", db_path)
    monkeypatch.setattr(auto_summarizer, "LOGS_DIR", tmp_path / "logs")
    source_registry.init_db()
    source_id = source_registry.add_source(
        url="https://example.com/k",
        title="클로드 요약",
        publisher="예시",
        content_preview="미리보기",
        content_body="한글 본문",
    )
    monkeypatch.setattr(auto_summarizer, "_get_provider", lambda: FakeProvider())
    result = auto_summarizer.summarize_source(source_id, levels=("oneliner",))
    assert isinstance(result["summary_oneliner"], str)
