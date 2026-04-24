from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from pipeline import citations_store, editorial_lint


class _Block:
    def __init__(self, text: str, citations: list[dict]) -> None:
        self.text = text
        self.citations = citations


class _Response:
    def __init__(self) -> None:
        self.content = [
            _Block(
                "Alpha claim",
                [
                    {
                        "type": "char_location",
                        "document_index": 0,
                        "cited_text": "Alpha quote",
                        "start_char_index": 1,
                        "end_char_index": 12,
                    }
                ],
            )
        ]


class _FakeHTTPResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


@pytest.fixture
def passing_article_runtime(monkeypatch: pytest.MonkeyPatch, fixture_json: callable) -> None:
    monkeypatch.setenv("CLAUDE_PROVIDER", "mock")

    class DummyProvider:
        name = "mock"

        def count_tokens(self, **_: object) -> int:
            return 16

        def complete_with_blocks(self, **_: object):
            return type("Result", (), {"text": "91"})()

    monkeypatch.setattr("pipeline.claude_provider.get_provider", lambda: DummyProvider())
    monkeypatch.setattr("pipeline.source_registry.list_sources", lambda article_id: [{"url": "https://example.com/source"}])
    monkeypatch.setattr(
        "requests.get",
        lambda url, timeout=10: _FakeHTTPResponse(
            'Alpha Corp reported 12% growth. The roadmap remains stable according to the company statement. 24 hours.'
        ),
    )
    (editorial_lint.LOGS_DIR / "factcheck_20260424_120000.json").write_text(
        json.dumps({"request_id": "req-1"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (citations_store.CITATIONS_DIR / "art-pass.json").write_text(
        json.dumps(fixture_json("citations", "art-pass.json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@pytest.mark.integration
def test_article_mode_full_run_has_11_items(fixture_text: callable, tmp_path: Path, passing_article_runtime) -> None:
    draft_path = tmp_path / "draft_pass.md"
    draft_path.write_text(fixture_text("drafts", "draft_pass.md"), encoding="utf-8")
    result = editorial_lint.lint_draft(str(draft_path), article_id="art-pass")
    assert len(result["items"]) == 11
    assert result["can_publish"] is True


@pytest.mark.integration
def test_card_news_mode_full_run_has_4_items(fixture_json: callable) -> None:
    payload = fixture_json("slides", "slides_pass.json")
    base = payload["slides"]
    slides = [base[0], base[1], base[2], base[1], base[2], base[1], base[3]]
    source_md = (
        "Alpha Corp shipped a new assistant and explained the rollout plan in detail.\n"
        "Admins can phase adoption team by team with enterprise controls.\n"
        "Governance, cost control, and workflow are all covered clearly.\n"
        "The enterprise controls and migration path are explained for teams.\n"
    )
    result = editorial_lint.lint_card_news(slides, source_md)
    assert len(result["items"]) == 4


@pytest.mark.integration
def test_only_mode_selects_two_checks(fixture_text: callable, tmp_path: Path, passing_article_runtime) -> None:
    draft_path = tmp_path / "draft_pass.md"
    draft_path.write_text(fixture_text("drafts", "draft_pass.md"), encoding="utf-8")
    result = editorial_lint.lint_draft(
        str(draft_path),
        only=["source-id", "citations-cross-check"],
        article_id="art-pass",
    )
    assert [item["id"] for item in result["items"]] == ["source-id", "citations-cross-check"]


@pytest.mark.integration
def test_main_json_output_and_strict_exit(fixture_text: callable, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, passing_article_runtime) -> None:
    draft_path = tmp_path / "draft_pass.md"
    draft_path.write_text(fixture_text("drafts", "draft_pass.md"), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["editorial_lint.py", "--draft", str(draft_path), "--article-id", "art-pass", "--json"],
    )
    exit_code = editorial_lint.main()
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert len(payload["items"]) == 11

    bad_path = tmp_path / "draft_fail.md"
    bad_path.write_text("# Fail\n\nNo source markers here.", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["editorial_lint.py", "--draft", str(bad_path), "--strict"],
    )
    assert editorial_lint.main() == 1


@pytest.mark.integration
def test_citations_store_roundtrip() -> None:
    document_map = [{"source_id": "src-alpha", "url": "https://example.com/a"}]
    path = citations_store.save_citations(
        article_id="art-roundtrip",
        request_id="req-1",
        provider="api",
        model="claude-opus-4-7",
        document_map=document_map,
        raw_response=_Response(),
    )
    payload = citations_store.load_citations("art-roundtrip")
    assert path.exists()
    assert payload["claims"][0]["citations"][0]["source_id"] == "src-alpha"


@pytest.mark.integration
def test_article_standards_and_ghost_fetch_paths(
    fixture_text: callable,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_path = tmp_path / "draft_pass.md"
    draft_path.write_text(fixture_text("drafts", "draft_pass.md"), encoding="utf-8")

    standards_mod = ModuleType("pipeline.standards_checker")
    standards_mod.check_article = lambda draft_path, category, metadata: {
        "can_publish": True,
        "must_pass_passed": 3,
        "must_pass_total": 3,
        "should_pass_passed": 2,
        "should_pass_total": 2,
        "common_checks": [{"id": "a", "status": "pass"}],
        "category_checks": [{"id": "b", "status": "pass"}],
    }
    ghost_mod = ModuleType("pipeline.ghost_client")
    ghost_mod._request = lambda method, path, params=None: {"posts": [{"title": "Ghost title", "html": "<p>Ghost body</p>"}]}
    monkeypatch.setitem(sys.modules, "pipeline.standards_checker", standards_mod)
    monkeypatch.setitem(sys.modules, "pipeline.ghost_client", ghost_mod)

    result = editorial_lint.lint_draft(
        str(draft_path),
        only=["source-id", "article-standards"],
        category="weekly",
        article_id="art-pass",
    )
    assert result["items"][-1]["id"] == "article-standards"
    assert result["items"][-1]["status"] == "pass"

    title, html = editorial_lint.fetch_ghost_post_html("post-1")
    assert title == "Ghost title"
    assert "Ghost body" in html


@pytest.mark.integration
def test_main_card_news_and_ghost_dry_run_branches(
    fixture_json: callable,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    slides_path = tmp_path / "slides.json"
    source_path = tmp_path / "source.md"
    slides_path.write_text(json.dumps(fixture_json("slides", "slides_pass.json"), ensure_ascii=False, indent=2), encoding="utf-8")
    source_path.write_text(
        "Alpha Corp shipped a new assistant and explained the rollout plan in detail.\n"
        "Admins can phase adoption team by team with enterprise controls.\n"
        "Governance, cost control, and workflow are all covered clearly.\n"
        "The enterprise controls and migration path are explained for teams.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["editorial_lint.py", "--mode", "card-news", "--slides-json", str(slides_path), "--source", str(source_path)],
    )
    assert editorial_lint.main() == 0
    output = capsys.readouterr().out
    assert "card-news-structure" in output

    monkeypatch.setattr(
        sys,
        "argv",
        ["editorial_lint.py", "--ghost-post-id", "post-1", "--dry-run"],
    )
    assert editorial_lint.main() == 2


@pytest.mark.integration
def test_log_helpers_and_warning_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (editorial_lint.LOGS_DIR / "factcheck_20260424_120000.json").write_text(
        json.dumps({"request_id": "req-helper"}, ensure_ascii=False),
        encoding="utf-8",
    )
    warn = editorial_lint.check_request_id_log(None, ghost_post_id="ghost-post")
    assert warn["status"] == "warn"

    log_file = editorial_lint._write_lint_log(
        mode="article",
        result={"passed": 1, "failed": 0, "warnings": 0, "can_publish": True, "items": []},
        draft_path=str(tmp_path / "draft.md"),
        article_id="art-helper",
        only=["source-id"],
    )
    assert log_file.exists()
    assert editorial_lint._derive_lint_article_id(str(tmp_path / "draft.md"), None, None) == "draft"

    standards_mod = ModuleType("pipeline.standards_checker")
    standards_mod.check_article = lambda draft_path, category, metadata: {
        "can_publish": False,
        "must_pass_passed": 1,
        "must_pass_total": 2,
        "should_pass_passed": 0,
        "should_pass_total": 1,
        "common_checks": [{"id": "a", "status": "fail"}],
        "category_checks": [{"id": "b", "status": "warn"}],
    }
    monkeypatch.setitem(sys.modules, "pipeline.standards_checker", standards_mod)
    failed = editorial_lint._check_article_standards(
        draft_path=str(tmp_path / "draft.md"),
        category="weekly",
        article_id="art-helper",
    )
    assert failed["status"] == "fail"


@pytest.mark.integration
def test_main_parser_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["editorial_lint.py"])
    with pytest.raises(SystemExit):
        editorial_lint.main()

    monkeypatch.setattr(
        sys,
        "argv",
        ["editorial_lint.py", "--draft", "draft.md", "--only", "unknown-check"],
    )
    with pytest.raises(SystemExit):
        editorial_lint.main()
