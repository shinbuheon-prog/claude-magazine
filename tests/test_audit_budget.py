"""Tests for scripts/audit_budget.py — illustration budget monitoring."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_audit_budget():
    path = Path(__file__).resolve().parents[1] / "scripts" / "audit_budget.py"
    spec = importlib.util.spec_from_file_location("audit_budget_test_module", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_cost(data_dir: Path, month: str, total: float, providers: dict) -> Path:
    path = data_dir / f"illustration_cost_{month}.json"
    path.write_text(
        json.dumps({"month": month, "total_usd": total, "providers": providers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_resolve_cap_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """env에서 cap 읽기. 잘못된 값은 default 0.0으로 fallback."""
    audit = _load_audit_budget()
    monkeypatch.setenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "5.0")
    assert audit.resolve_cap() == 5.0
    # override 우선
    assert audit.resolve_cap(10.0) == 10.0
    # 음수 → 0 clamp
    assert audit.resolve_cap(-5.0) == 0.0
    # invalid env → default
    monkeypatch.setenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "not-a-number")
    assert audit.resolve_cap() == audit.DEFAULT_CAP


def test_utilization_returns_none_for_zero_cap() -> None:
    """cap=0 (무료-only 모드)는 utilization 비율 무의미 → None."""
    audit = _load_audit_budget()
    assert audit.utilization(0.0, 0.0) is None
    assert audit.utilization(5.0, 0.0) is None
    assert audit.utilization(0.0, 10.0) == 0.0
    assert audit.utilization(8.0, 10.0) == 0.8


def test_read_illustration_cost_returns_zero_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """파일 부재 시 zero 페이로드 반환."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    result = audit.read_illustration_cost("2026-04")
    assert result["month"] == "2026-04"
    assert result["total_usd"] == 0.0
    assert result["providers"] == {}


def test_read_illustration_cost_handles_corrupt_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """잘못된 JSON 파일 → zero 페이로드 fallback (raise 안 함)."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    bad = tmp_path / "illustration_cost_2026-04.json"
    bad.write_text("not valid json", encoding="utf-8")
    result = audit.read_illustration_cost("2026-04")
    assert result["total_usd"] == 0.0


def test_render_text_under_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """텍스트 출력 — cap 미달 시 경고 없음."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 2.0, {"openai": 2.0})
    cost = audit.read_illustration_cost("2026-04")
    text = audit.render_text("2026-04", cost, cap=10.0)
    assert "Illustration Budget Audit (2026-04)" in text
    assert "$2.0000" in text
    assert "20.0%" in text
    assert "EXCEEDED" not in text
    assert "APPROACHING" not in text


def test_render_text_approaching_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """80% 이상 utilization 시 APPROACHING 경고."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 8.5, {"openai": 8.5})
    cost = audit.read_illustration_cost("2026-04")
    text = audit.render_text("2026-04", cost, cap=10.0)
    assert "APPROACHING" in text
    assert "85.0%" in text


def test_render_text_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cap 초과 시 EXCEEDED 메시지 + 초과 금액."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 12.0, {"openai": 12.0})
    cost = audit.read_illustration_cost("2026-04")
    text = audit.render_text("2026-04", cost, cap=10.0)
    assert "EXCEEDED" in text
    assert "$2.0000 over cap" in text


def test_render_text_zero_cap_free_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cap=0 (무료-only 모드) 표기."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 0.0, {"placeholder": 0.0, "pollinations": 0.0})
    cost = audit.read_illustration_cost("2026-04")
    text = audit.render_text("2026-04", cost, cap=0.0)
    assert "free-only mode" in text
    # provider 분포는 표시
    assert "placeholder:" in text
    assert "pollinations:" in text


def test_render_json_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON 출력 스키마 일관성 검증."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 3.0, {"huggingface": 3.0})
    cost = audit.read_illustration_cost("2026-04")
    payload = audit.render_json("2026-04", cost, cap=5.0)
    assert payload["month"] == "2026-04"
    assert payload["total_usd"] == 3.0
    assert payload["cap_usd"] == 5.0
    assert payload["utilization"] == 0.6
    assert payload["exceeded"] is False
    assert payload["approaching"] is False
    assert "huggingface" in payload["providers"]


def test_notify_slack_silent_when_webhook_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """webhook 미설정 시 silent skip."""
    audit = _load_audit_budget()
    monkeypatch.delenv("NOTIFY_SLACK_WEBHOOK", raising=False)
    # 호출이 예외 없으면 OK
    audit.notify_slack("2026-04", 9.0, 10.0, 0.9)


def test_notify_slack_skipped_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """utilization < 80% 시 알림 보내지 않음 (notify가 silently skip)."""
    audit = _load_audit_budget()
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example/test")
    captured: dict[str, object] = {}
    import types
    fake_requests = types.SimpleNamespace(post=lambda *a, **kw: captured.setdefault("called", True))
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    audit.notify_slack("2026-04", 5.0, 10.0, 0.5)
    assert "called" not in captured


def test_notify_slack_posts_when_approaching(monkeypatch: pytest.MonkeyPatch) -> None:
    """80% 이상 시 Slack post 호출."""
    audit = _load_audit_budget()
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example/test")
    captured: dict[str, object] = {}
    import types
    def fake_post(url, json=None, timeout=None, **_):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=fake_post))
    audit.notify_slack("2026-04", 8.5, 10.0, 0.85)
    assert captured["url"] == "https://hooks.example/test"
    assert captured["timeout"] == 10
    body = captured["json"]
    assert "APPROACHING" in body["text"]
    assert "$8.50" in body["text"]
    assert "85.0%" in body["text"]


def test_notify_slack_says_exceeded_when_over_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """cap 초과 시 EXCEEDED 메시지."""
    audit = _load_audit_budget()
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example/test")
    captured: dict[str, object] = {}
    import types
    def fake_post(url, json=None, **_):
        captured["json"] = json
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=fake_post))
    audit.notify_slack("2026-04", 12.0, 10.0, 1.2)
    assert "EXCEEDED" in captured["json"]["text"]


def test_main_strict_exits_one_when_cap_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """--strict + cap 초과 → exit code 1."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 12.0, {"openai": 12.0})
    monkeypatch.setattr(sys, "argv", ["audit_budget.py", "--month", "2026-04", "--cap", "10.0", "--strict"])
    rc = audit.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "EXCEEDED" in out


def test_main_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """--json 플래그로 JSON 출력 + exit 0 (under cap)."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    _write_cost(tmp_path, "2026-04", 1.0, {"pollinations": 1.0})
    monkeypatch.setattr(sys, "argv", ["audit_budget.py", "--month", "2026-04", "--cap", "5.0", "--json"])
    rc = audit.main()
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["total_usd"] == 1.0
    assert payload["cap_usd"] == 5.0
    assert payload["exceeded"] is False


def test_main_default_zero_cap_passes_with_zero_cost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """기본 cap=0 (무료-only) + 비용 0 → exit 0."""
    audit = _load_audit_budget()
    monkeypatch.setattr(audit, "DATA_DIR", tmp_path)
    monkeypatch.delenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", raising=False)
    monkeypatch.setattr(sys, "argv", ["audit_budget.py", "--month", "2026-04"])
    rc = audit.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "free-only mode" in out
