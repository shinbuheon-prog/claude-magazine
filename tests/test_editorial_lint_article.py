from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline import citations_store, editorial_lint


def _write_citations(article_id: str, payload: dict) -> None:
    path = citations_store.CITATIONS_DIR / f"{article_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


@pytest.mark.article
def test_source_id_pass_fail_edge() -> None:
    passed = editorial_lint.check_source_id("A sourced claim appears here [src-a1].")
    failed = editorial_lint.check_source_id("A sourced claim appears here without marker.")
    edge = editorial_lint.check_source_id("# Heading only")
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"
    assert edge["status"] == "warn"


@pytest.mark.article
def test_citations_cross_check_pass_warn_missing_warn_mismatch(fixture_json: callable) -> None:
    _write_citations("art-pass", fixture_json("citations", "art-pass.json"))
    passed = editorial_lint.check_citations_cross_check("Alpha [src-alpha] and Beta [src-beta].", article_id="art-pass")
    missing = editorial_lint.check_citations_cross_check("Alpha [src-alpha].", article_id="art-missing")
    _write_citations("art-mismatch", fixture_json("citations", "art-mismatch.json"))
    mismatch = editorial_lint.check_citations_cross_check("Alpha [src-alpha] Beta [src-beta].", article_id="art-mismatch")
    assert passed["status"] == "pass"
    assert missing["status"] == "warn"
    assert mismatch["status"] == "warn"


@pytest.mark.article
def test_translation_guard_pass_warn() -> None:
    passed = editorial_lint.check_translation_guard("Normal paragraph.\nAnother line.")
    warned = editorial_lint.check_translation_guard("> one\n> two\n> three\nParagraph.")
    assert passed["status"] == "pass"
    assert warned["status"] == "warn"


@pytest.mark.article
def test_title_body_match_warn_and_pass(monkeypatch: pytest.MonkeyPatch, dummy_provider) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_PROVIDER", "api")
    warned = editorial_lint.check_title_body_match("# Title\n\nBody text [src-a].")
    monkeypatch.setenv("CLAUDE_PROVIDER", "mock")
    monkeypatch.setattr("pipeline.claude_provider.get_provider", lambda: dummy_provider)
    passed = editorial_lint.check_title_body_match("# Title\n\nBody text [src-a].")
    assert warned["status"] == "warn"
    assert passed["status"] == "pass"


@pytest.mark.article
def test_quote_fidelity_pass_fail_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipeline.source_registry.list_sources", lambda article_id: [{"url": "https://example.com/source"}])
    monkeypatch.setattr("requests.get", lambda url, timeout=10: _FakeResponse('The report says "Stable roadmap".'))
    passed = editorial_lint.check_quote_fidelity('The report says "Stable roadmap".', article_id="art-1")
    failed = editorial_lint.check_quote_fidelity('The report says "Wrong quote".', article_id="art-1")
    warned = editorial_lint.check_quote_fidelity('The report says "Stable roadmap".')
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"
    assert warned["status"] == "warn"


@pytest.mark.article
def test_no_fabrication_pass_fail_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    body = "Alpha Corp revenue reached 12% in the quarter."
    monkeypatch.setattr("pipeline.source_registry.list_sources", lambda article_id: [{"url": "https://example.com/source"}])
    monkeypatch.setattr("requests.get", lambda url, timeout=10: _FakeResponse(body))
    passed = editorial_lint.check_no_fabrication(body, article_id="art-1")
    failed = editorial_lint.check_no_fabrication("Beta Corp revenue reached 42% in the quarter.", article_id="art-1")
    warned = editorial_lint.check_no_fabrication("Alpha Corp reached 12% growth.")
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"
    assert warned["status"] == "warn"


@pytest.mark.article
def test_pii_check_pass_fail() -> None:
    passed = editorial_lint.check_pii("Contact editorial@example.com for corrections.")
    failed = editorial_lint.check_pii("Reach me at 010-1234-5678 or foo@example.com.")
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.article
def test_image_rights_pass_fail() -> None:
    passed = editorial_lint.check_image_rights('<img src="a.png" data-rights="licensed" alt="a" />')
    failed = editorial_lint.check_image_rights('![chart](chart.png)\n<img src="b.png" alt="b" />')
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.article
def test_ai_disclosure_pass_fail() -> None:
    passed = editorial_lint.check_ai_disclosure("Lead\n\n## AI 사용 고지\n이 기사는 AI 보조 도구인 Claude를 사용했습니다.")
    failed = editorial_lint.check_ai_disclosure("Lead\n\nNo disclosure here.")
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.article
def test_correction_policy_pass_fail() -> None:
    passed = editorial_lint.check_correction_policy("정정 요청: editorial@example.com 24 hours 안에 검토합니다.")
    failed = editorial_lint.check_correction_policy("연락처만 있고 기한이 없습니다: editorial@example.com")
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.article
def test_request_id_log_pass_fail(tmp_path: Path) -> None:
    draft = tmp_path / "draft_20260424_sample.md"
    draft.write_text("# Title\n\nBody [src-a].", encoding="utf-8")
    (editorial_lint.LOGS_DIR / "factcheck_20260424_120000.json").write_text(
        json.dumps({"request_id": "req-1"}, ensure_ascii=False),
        encoding="utf-8",
    )
    passed = editorial_lint.check_request_id_log(str(draft))
    (editorial_lint.LOGS_DIR / "factcheck_20260424_120000.json").unlink()
    failed = editorial_lint.check_request_id_log(str(draft))
    assert passed["status"] == "pass"
    assert failed["status"] == "fail"


@pytest.mark.article
def test_lint_draft_reads_bom(fixture_text: callable, tmp_path: Path) -> None:
    draft_path = tmp_path / "draft_bom.md"
    draft_path.write_text(fixture_text("drafts", "draft_mojibake.md"), encoding="utf-8")
    result = editorial_lint.lint_draft(str(draft_path), only=["source-id"], article_id="art-bom")
    assert result["items"][0]["status"] == "pass"


@pytest.mark.article
def test_helpers_strip_html_split_sentences_and_format_report() -> None:
    html = '<p>Lead</p><img src="a.png" alt="a" data-rights="licensed" /><p>Tail</p>'
    stripped = editorial_lint._strip_html(html)
    assert "<img" in stripped
    text = (
        "# Head\n\n"
        "Claim sentence with marker [src-a]. Another claim with marker [src-b].\n\n"
        "## AI 사용 고지\n"
        "이 아래 문장은 검증 대상에서 제외됩니다.\n"
    )
    sentences = editorial_lint._split_sentences(text)
    assert all("제외" not in sentence for sentence in sentences)
    report = editorial_lint.format_report(
        {"passed": 1, "failed": 1, "warnings": 0, "can_publish": False, "items": [{"id": "source-id", "status": "fail", "message": "missing", "details": ["A"]}]},
        draft_path="draft.md",
    )
    assert "draft.md" in report
    assert "source-id" in report


@pytest.mark.article
def test_translation_guard_warns_when_quote_run_reaches_eof() -> None:
    warned = editorial_lint.check_translation_guard("> one\n> two\n> three")
    assert warned["status"] == "warn"


@pytest.mark.article
def test_title_body_match_fail_when_title_or_body_missing() -> None:
    missing_title = editorial_lint.check_title_body_match("Body text only [src-a].")
    missing_body = editorial_lint.check_title_body_match("# Title only")
    assert missing_title["status"] == "fail"
    assert missing_body["status"] == "fail"


@pytest.mark.article
def test_ai_disclosure_fails_on_empty_document() -> None:
    failed = editorial_lint.check_ai_disclosure("")
    assert failed["status"] == "fail"


@pytest.mark.article
def test_citations_cross_check_warn_when_manual_or_cited_ids_missing(fixture_json: callable) -> None:
    _write_citations("art-pass", fixture_json("citations", "art-pass.json"))
    _write_citations("art-no-cited", {"claims": [{"claim_text": "Alpha", "citations": [{"source_id": None}]}]})
    no_manual = editorial_lint.check_citations_cross_check("Alpha claim without marker.", article_id="art-pass")
    no_cited = editorial_lint.check_citations_cross_check("Alpha [src-alpha].", article_id="art-no-cited")
    assert no_manual["status"] == "warn"
    assert no_cited["status"] == "warn"
