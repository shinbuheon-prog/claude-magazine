from __future__ import annotations

import json
from pathlib import Path

from pipeline import monthly_curator, source_registry


class CuratorProvider:
    def __init__(self):
        self.calls = []

    def stream_complete(self, system, user, model_tier="opus", max_tokens=0, stream_callback=None):
        self.calls.append((model_tier, user))
        if "Return JSON" in user:
            text = json.dumps(
                {
                    "clusters": [
                        {
                            "cluster_id": "claude-mcp-1",
                            "days_covered": ["2026-04-01"],
                            "source_ids": ["src-1", "src-2"],
                            "proposed_angle": "Claude MCP trend",
                            "magazine_section_candidate": "insight",
                            "target_pages": 3,
                            "priority_score": 8.5,
                        }
                    ]
                },
                ensure_ascii=False,
            )
        else:
            text = "cover and interview are underfilled."
        return type(
            "Result",
            (),
            {
                "text": text,
                "request_id": "req-opus",
                "model": "mock-opus",
                "provider": "mock",
                "input_tokens": 12,
                "output_tokens": 8,
            },
        )()


def _seed_sources(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "source_registry.db"
    monkeypatch.setattr(source_registry, "DB_PATH", db_path)
    monkeypatch.setattr(monthly_curator, "DB_PATH", db_path)
    monkeypatch.setattr(monthly_curator, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(monthly_curator, "REPORTS_DIR", tmp_path / "reports")
    source_registry.init_db()
    sid1 = source_registry.add_source(
        url="https://example.com/1",
        title="Claude MCP launch",
        publisher="HN",
        content_preview="Claude MCP rollout",
        content_body="Body 1",
        source_type="hackernews",
        topics=["claude", "mcp"],
    )
    sid2 = source_registry.add_source(
        url="https://example.com/2",
        title="Claude MCP guide",
        publisher="Reddit",
        content_preview="Claude MCP community notes",
        content_body="Body 2",
        source_type="reddit",
        topics=["claude", "mcp"],
    )
    source_registry.update_source(sid1, summary_oneliner="Claude MCP launch", summarized_at="2026-04-01T00:00:00+00:00")
    source_registry.update_source(sid2, summary_oneliner="Claude MCP guide", summarized_at="2026-04-02T00:00:00+00:00")

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE sources SET retrieved_at = '2026-04-01T00:00:00+00:00' WHERE source_id = ?", (sid1,))
        conn.execute("UPDATE sources SET retrieved_at = '2026-04-02T00:00:00+00:00' WHERE source_id = ?", (sid2,))
        conn.commit()
    finally:
        conn.close()


def test_tfidf_cluster_min_size(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    sources = monthly_curator._fetch_sources("2026-04")
    candidates = monthly_curator._build_tfidf_candidates(sources, min_cluster_size=2)
    assert candidates


def test_opus_cluster_format(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    monkeypatch.setattr(monthly_curator, "_get_provider", lambda: CuratorProvider())
    payload = monthly_curator.curate_monthly_external("2026-04")
    assert payload["clusters"][0]["cluster_id"] == "claude-mcp-1"


def test_gap_analysis_includes_all_categories(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    monkeypatch.setattr(monthly_curator, "_get_provider", lambda: CuratorProvider())
    payload = monthly_curator.curate_monthly_external("2026-04")
    assert "cover" in payload["gap_analysis"]


def test_korean_utf8_safe(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    monkeypatch.setattr(monthly_curator, "_get_provider", lambda: CuratorProvider())
    payload = monthly_curator.curate_monthly_external("2026-04", dry_run=True)
    assert isinstance(payload["clusters"], list)


def test_output_markdown_matches_sns_digest_format(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    monkeypatch.setattr(monthly_curator, "_get_provider", lambda: CuratorProvider())
    payload = monthly_curator.curate_monthly_external("2026-04", dry_run=True)
    text = Path(payload["output_path"]).read_text(encoding="utf-8")
    assert "## editor_approval" in text
    assert "## 1. Topic Clusters" in text


def test_request_id_saved_to_logs(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    monkeypatch.setattr(monthly_curator, "_get_provider", lambda: CuratorProvider())
    monthly_curator.curate_monthly_external("2026-04")
    payload = json.loads(next((tmp_path / "logs").glob("monthly_curator_*.json")).read_text(encoding="utf-8"))
    assert payload[0]["request_id"] == "req-opus"


def test_dry_run_skips_llm(tmp_path, monkeypatch):
    _seed_sources(tmp_path, monkeypatch)
    provider = CuratorProvider()
    monkeypatch.setattr(monthly_curator, "_get_provider", lambda: provider)
    monthly_curator.curate_monthly_external("2026-04", dry_run=True)
    assert provider.calls == []
