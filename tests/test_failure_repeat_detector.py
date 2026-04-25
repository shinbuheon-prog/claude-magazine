from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _load_detector() -> object:
    path = Path(__file__).resolve().parents[1] / "pipeline" / "failure_repeat_detector.py"
    spec = importlib.util.spec_from_file_location("failure_repeat_detector_test_module", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_failure_report(path: Path, month: str, stage: str, failure_class: str, failed_at: str, error_output: str) -> None:
    path.write_text(
        "\n".join(
            [
                "# Publish Failure Recovery Guide",
                "",
                f"- Month: {month}",
                f"- Failed stage: {stage}",
                f"- Failure time: {failed_at}",
                f"- Matched class: {failure_class}",
                "",
                "## Error Output",
                "",
                "```text",
                error_output,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_scan_detect_and_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_detector()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(module, "QUEUE_DIR", reports_dir / "auto_trigger_queue")
    monkeypatch.setattr(module, "ARCHIVE_DIR", reports_dir / "auto_trigger_queue" / "archived")

    _write_failure_report(
        reports_dir / "failure_2026-04_pdf_compile.md",
        "2026-04",
        "pdf_compile",
        "puppeteer_timeout",
        "2026-04-20T10:00:00+00:00",
        "TimeoutError sk-ant-secret",
    )
    _write_failure_report(
        reports_dir / "failure_2026-05_pdf_compile.md",
        "2026-05",
        "pdf_compile",
        "puppeteer_timeout",
        "2026-04-22T10:00:00+00:00",
        "TimeoutError figd_token",
    )
    _write_failure_report(
        reports_dir / "failure_2026-05_ghost_publish.md",
        "2026-05",
        "ghost_publish",
        "jwt_401",
        "2026-04-23T10:00:00+00:00",
        "401 Unauthorized",
    )

    class _FrozenDateTime(module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 25, 12, 0, 0, tzinfo=tz or module.timezone.utc)

    monkeypatch.setattr(module, "datetime", _FrozenDateTime)

    failures = module.scan_failures(window_days=14)
    assert len(failures) == 3
    assert failures[0]["report_path"] == "reports/failure_2026-04_pdf_compile.md"
    assert "sk-ant-secret" not in failures[0]["error_excerpt"]

    grouped = module.count_by_class(failures)
    assert list(grouped) == ["puppeteer_timeout", "jwt_401"]
    assert len(grouped["puppeteer_timeout"]) == 2

    repeats = module.detect_repeats(failures, threshold=2, window_days=14)
    assert len(repeats) == 1
    assert repeats[0]["class"] == "puppeteer_timeout"
    assert repeats[0]["count"] == 2
    assert repeats[0]["stages"] == ["pdf_compile"]


def test_write_and_acknowledge_marker_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_detector()
    reports_dir = tmp_path / "reports"
    queue_dir = reports_dir / "auto_trigger_queue"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(module, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(module, "ARCHIVE_DIR", queue_dir / "archived")

    class _FrozenDateTime(module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 25, 13, 30, 0, tzinfo=tz or module.timezone.utc)

    monkeypatch.setattr(module, "datetime", _FrozenDateTime)
    repeats = [
        {
            "class": "puppeteer_timeout",
            "count": 3,
            "stages": ["pdf_compile"],
            "first_seen": "2026-04-20T10:00:00+00:00",
            "last_seen": "2026-04-25T10:00:00+00:00",
            "occurrences": [{"month": "2026-05", "stage": "pdf_compile", "ts": "2026-04-25T10:00:00+00:00", "report_path": "reports/failure_2026-05_pdf_compile.md"}],
            "window_days": 14,
        }
    ]

    first = module.write_queue_marker(repeats, detected_at_run="publish_monthly:2026-05")
    second = module.write_queue_marker(repeats, detected_at_run="publish_monthly:2026-05")
    assert first is not None
    assert first == second
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["status"] == "queued"

    module.acknowledge_marker(first)
    archived = queue_dir / "archived" / first.name
    assert archived.exists()
    archived_payload = json.loads(archived.read_text(encoding="utf-8"))
    assert archived_payload["status"] == "processed"
    assert not first.exists()


def test_cli_json_output(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_failure_report(
        reports_dir / "failure_2026-05_pdf_compile.md",
        "2026-05",
        "pdf_compile",
        "puppeteer_timeout",
        "2026-04-25T10:00:00+00:00",
        "TimeoutError",
    )
    _write_failure_report(
        reports_dir / "failure_2026-05_ghost_publish.md",
        "2026-05",
        "ghost_publish",
        "puppeteer_timeout",
        "2026-04-24T10:00:00+00:00",
        "TimeoutError",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "pipeline" / "failure_repeat_detector.py"),
            "--window",
            "30",
            "--threshold",
            "2",
            "--json",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env={**dict(os.environ), "CLAUDE_MAGAZINE_REPORTS_DIR": str(reports_dir)},
    )
    payload = json.loads(completed.stdout)
    assert payload["repeat_count"] == 1
    assert payload["repeats"][0]["class"] == "puppeteer_timeout"
