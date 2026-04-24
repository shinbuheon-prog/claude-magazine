from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from pipeline import failure_playbook


def _load_publish_monthly() -> object:
    path = Path(__file__).resolve().parents[1] / "scripts" / "publish_monthly.py"
    spec = importlib.util.spec_from_file_location("publish_monthly_test_module_task051", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.integration
def test_failure_playbook_spec_and_matching() -> None:
    payload = failure_playbook.load_failure_playbook()
    assert "quality_gate" in payload["stages"]
    assert failure_playbook.match_failure_class("ghost_publish", "401 Unauthorized from Ghost") == "jwt_401"


@pytest.mark.integration
def test_failure_playbook_redacts_tokens_and_renders_commands() -> None:
    text = failure_playbook.redact_sensitive_text("sk-ant-secret figd_token abcdefabcdefabcdefabcdef:abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd")
    assert "sk-ant-***" in text
    assert "figd_***" in text
    assert "kid:***" in text

    report = failure_playbook.generate_failure_report(
        "2026-05",
        "pdf_compile",
        "TimeoutError from puppeteer with sk-ant-secret",
        "reports/publish_state_2026-05.json",
    )
    assert "Matched class: puppeteer_timeout" in report
    assert "publish_monthly.py --month 2026-05 --reset-stage pdf_compile --yes" in report
    assert "sk-ant-secret" not in report


@pytest.mark.integration
def test_publish_monthly_writes_failure_playbook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_publish_monthly()
    monkeypatch.setattr(module, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(module, "ISSUES_DIR", tmp_path / "issues")
    (tmp_path / "reports").mkdir()
    (tmp_path / "issues").mkdir()
    (tmp_path / "issues" / "2026-05.yml").write_text(
        "issue: 2026-05\ntheme: Test\neditor_in_chief: Editor\narticles:\n  - slug: draft-a\n    status: draft\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["publish_monthly.py", "--month", "2026-05"])
    assert module.main() == 1
    failure_path = (tmp_path / "reports" / "failure_2026-05_quality_gate.md")
    assert failure_path.exists()
    assert "Quality gate failed" not in failure_path.read_text(encoding="utf-8")
    assert "status=draft" in failure_path.read_text(encoding="utf-8")
