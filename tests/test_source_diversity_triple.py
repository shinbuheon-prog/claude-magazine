from __future__ import annotations

from pipeline import source_diversity, source_registry


def _sources(opposing_stance: str = "con"):
    return [
        {"language": "ko", "is_official": 1, "stance": "neutral", "publisher": "KISA", "retrieved_at": "2026-04-20T00:00:00+00:00"},
        {"language": "en", "is_official": 1, "stance": "neutral", "publisher": "Anthropic", "retrieved_at": "2024-01-01T00:00:00+00:00"},
        {"language": "ko", "is_official": 0, "stance": opposing_stance, "publisher": "Community", "retrieved_at": "2026-04-21T00:00:00+00:00"},
    ]


def test_triple_pattern_all_present_passes():
    result = source_diversity.check_triple_pattern(_sources())
    assert result["status"] == "pass"


def test_missing_korean_official_fails():
    sources = _sources()
    sources[0]["is_official"] = 0
    result = source_diversity.check_triple_pattern(sources)
    assert "korean_official" in result["details"]["missing_categories"]


def test_missing_source_official_fails():
    sources = _sources()
    sources[1]["is_official"] = 0
    result = source_diversity.check_triple_pattern(sources)
    assert "source_official" in result["details"]["missing_categories"]


def test_missing_opposing_fails():
    sources = _sources(opposing_stance="neutral")
    result = source_diversity.check_triple_pattern(sources)
    assert "opposing_or_affected" in result["details"]["missing_categories"]


def test_affected_stance_counts_as_opposing():
    result = source_diversity.check_triple_pattern(_sources(opposing_stance="affected"))
    assert result["status"] == "pass"


def test_self_content_exception_with_editor_approval():
    sources = _sources(opposing_stance="neutral")
    result = source_diversity.check_triple_pattern(sources, editor_approved_exception=True)
    assert result["status"] == "pass"
    assert result["details"]["editor_approved_exception"] is True


def test_5_rules_integrated_check():
    result = source_diversity.check_diversity_from_files([], editor_approved_exception=True)
    assert "rules" in result
    assert len(result["rules"]) == 5


def test_source_registry_allows_affected_stance(tmp_path, monkeypatch):
    monkeypatch.setattr(source_registry, "DB_PATH", tmp_path / "source_registry.db")
    source_registry.init_db()
    source_id = source_registry.add_source(url="https://example.com/1", content_preview="preview")
    assert source_registry.update_source(source_id, stance="affected") is True
