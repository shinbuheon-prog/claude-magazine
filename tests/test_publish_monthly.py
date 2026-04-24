from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_publish_monthly() -> object:
    path = Path(__file__).resolve().parents[1] / "scripts" / "publish_monthly.py"
    spec = importlib.util.spec_from_file_location("publish_monthly_test_module", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.integration
def test_publish_monthly_status_and_reset_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    module = _load_publish_monthly()
    monkeypatch.setattr(module, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(module, "ISSUES_DIR", tmp_path / "issues")
    (tmp_path / "reports").mkdir()
    state_path = module._state_path("2026-05")
    state_path.write_text(
        json.dumps(
            {
                "month": "2026-05",
                "stages": {"plan_loaded": True, "quality_gate": {"passed": 2, "failed": 0}},
                "telemetry": {"quality_gate": {"duration_sec": 1.2, "cost_usd": 0.0}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["publish_monthly.py", "--month", "2026-05", "--status", "--strict"])
    assert module.main() == 1
    assert "quality_gate" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["publish_monthly.py", "--month", "2026-05", "--reset-stage", "quality_gate", "--yes"])
    assert module.main() == 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "quality_gate" not in state["stages"]
    assert "quality_gate" not in state["telemetry"]


@pytest.mark.integration
def test_publish_monthly_from_stage_skips_earlier_stages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_publish_monthly()
    monkeypatch.setattr(module, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(module, "ISSUES_DIR", tmp_path / "issues")
    monkeypatch.setattr(module, "LOGS_DIR", tmp_path / "logs")
    (tmp_path / "reports").mkdir()
    (tmp_path / "issues").mkdir()
    (tmp_path / "logs").mkdir(exist_ok=True)
    (tmp_path / "issues" / "2026-05.yml").write_text(
        "issue: 2026-05\ntheme: Test\neditor_in_chief: Editor\narticles: []\n",
        encoding="utf-8",
    )

    # stage_pdf_compile은 scripts/compile_monthly_pdf.py를 subprocess로 호출하는데,
    # subprocess는 monkeypatched ISSUES_DIR를 상속받지 못하고 실제 repo 경로를 참조.
    # CI fresh checkout에는 drafts/issues/가 없으므로(gitignore) subprocess가 실패.
    # 테스트 목적(--from-stage가 앞 stage skip)만 검증하기 위해 subprocess 호출을 mock.
    class _MockCompleted:
        returncode = 0

    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: _MockCompleted())

    monkeypatch.setattr(sys, "argv", ["publish_monthly.py", "--month", "2026-05", "--from-stage", "pdf_compile", "--dry-run", "--yes"])
    assert module.main() == 0
    state = json.loads(module._state_path("2026-05").read_text(encoding="utf-8"))
    assert "pdf_compile" in state["telemetry"]
    assert "plan_loaded" not in state["telemetry"]
