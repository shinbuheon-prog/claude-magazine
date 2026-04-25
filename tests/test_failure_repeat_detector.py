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


def test_notify_slack_silent_when_webhook_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """NOTIFY_SLACK_WEBHOOK 미설정 시 무음 skip — 큐 마커 작성에 영향 없음."""
    module = _load_detector()
    monkeypatch.delenv("NOTIFY_SLACK_WEBHOOK", raising=False)
    # 호출이 어떤 예외도 던지지 않으면 OK
    module.notify_slack([{"class": "test", "count": 3}], tmp_path / "dummy.json")


def test_notify_slack_posts_when_webhook_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """webhook 설정 시 requests.post 호출 + 페이로드에 클래스 정보 포함."""
    module = _load_detector()
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example.com/test")

    captured: dict[str, object] = {}

    class _MockResponse:
        status_code = 200

    def fake_post(url, json=None, timeout=None, **_):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _MockResponse()

    import types

    fake_requests = types.SimpleNamespace(post=fake_post)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    module.notify_slack(
        [
            {"class": "puppeteer_timeout", "count": 4},
            {"class": "jwt_401", "count": 3},
        ],
        tmp_path / "marker_2026-04-25.json",
    )

    assert captured["url"] == "https://hooks.example.com/test"
    assert captured["timeout"] == 10
    body = captured["json"]
    assert isinstance(body, dict)
    assert "puppeteer_timeout(4)" in body["text"]
    assert "jwt_401(3)" in body["text"]
    assert "marker_2026-04-25.json" in body["text"]


def test_cli_text_mode_no_repeats(tmp_path: Path) -> None:
    """텍스트 모드(--json 없이) + 빈 reports 디렉터리 → 'none' 출력."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "pipeline" / "failure_repeat_detector.py"),
            "--window",
            "30",
            "--threshold",
            "2",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env={**dict(os.environ), "CLAUDE_MAGAZINE_REPORTS_DIR": str(reports_dir)},
    )
    assert "Repeated failures in last" in completed.stdout
    assert "- none" in completed.stdout


def test_cli_text_mode_with_repeats(tmp_path: Path) -> None:
    """텍스트 모드 + 반복 실패 ≥ 임계 → 클래스·count·last_seen 출력."""
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
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env={**dict(os.environ), "CLAUDE_MAGAZINE_REPORTS_DIR": str(reports_dir)},
    )
    assert "puppeteer_timeout count=2" in completed.stdout
    assert "pdf_compile" in completed.stdout
    assert "ghost_publish" in completed.stdout


def test_trigger_improvement_aborts_without_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    """confirmation prompt 거부 시 weekly_improvement 미실행 (return 1)."""
    module = _load_detector()
    # input() 호출이 'n' 응답하도록 stub
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    rc = module._trigger_weekly_improvement(yes=False)
    assert rc == 1


def test_trigger_improvement_with_yes_invokes_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """--yes 플래그 시 confirmation skip + subprocess.run 호출."""
    module = _load_detector()
    captured: dict[str, object] = {}

    class _MockCompleted:
        returncode = 0

    def fake_run(cmd, cwd=None, **_):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return _MockCompleted()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    rc = module._trigger_weekly_improvement(yes=True)
    assert rc == 0
    assert "weekly_improvement.py" in str(captured["cmd"])


def test_write_queue_marker_returns_none_for_empty_repeats(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """빈 repeats 리스트 → 마커 작성 안 함, None 반환."""
    module = _load_detector()
    monkeypatch.setattr(module, "QUEUE_DIR", tmp_path / "auto_trigger_queue")
    monkeypatch.setattr(module, "ARCHIVE_DIR", tmp_path / "auto_trigger_queue" / "archived")
    assert module.write_queue_marker([]) is None


def test_notify_slack_silent_on_requests_import_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """requests 미설치 환경에서도 큐 마커 작성에 영향 없음 (silent skip)."""
    module = _load_detector()
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example.com/test")
    # requests를 sys.modules에서 제거하고 import 실패 유도
    monkeypatch.setitem(sys.modules, "requests", None)
    # 호출이 어떤 예외도 던지지 않으면 OK
    module.notify_slack([{"class": "x", "count": 3}], tmp_path / "marker.json")


def test_trigger_improvement_accepts_yes_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """confirmation prompt에 'y' 응답 시 weekly_improvement 실행 분기 진입."""
    module = _load_detector()
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    captured: dict[str, object] = {}

    class _MockCompleted:
        returncode = 0

    monkeypatch.setattr(module.subprocess, "run", lambda cmd, cwd=None, **_: (captured.setdefault("cmd", cmd), _MockCompleted())[1])
    rc = module._trigger_weekly_improvement(yes=False)
    assert rc == 0
    assert captured.get("cmd") is not None


def test_resolve_helpers_use_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """env 변수 fallback + 잘못된 값일 때 기본값 사용."""
    module = _load_detector()

    monkeypatch.setenv("CLAUDE_MAGAZINE_FAILURE_WINDOW_DAYS", "21")
    monkeypatch.setenv("CLAUDE_MAGAZINE_FAILURE_THRESHOLD", "5")
    assert module.resolve_window_days() == 21
    assert module.resolve_threshold() == 5

    # 명시값 우선
    assert module.resolve_window_days(7) == 7
    assert module.resolve_threshold(2) == 2

    # 음수·invalid → env, env 잘못되면 default
    monkeypatch.setenv("CLAUDE_MAGAZINE_FAILURE_WINDOW_DAYS", "abc")
    assert module.resolve_window_days() == module.DEFAULT_WINDOW_DAYS
    monkeypatch.setenv("CLAUDE_MAGAZINE_FAILURE_THRESHOLD", "-1")
    assert module.resolve_threshold() == module.DEFAULT_THRESHOLD
