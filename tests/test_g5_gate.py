from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline import g5_gate
from scripts import audit_budget


def _write_article_cost(tmp_path: Path, article_id: str, total_cost: float, budget: float = 1.0) -> Path:
    cost_dir = tmp_path / "cost_tracking"
    cost_dir.mkdir(exist_ok=True)
    path = cost_dir / f"article_{article_id}_costs.json"
    path.write_text(
        json.dumps(
            {
                "article_id": article_id,
                "estimated_budget_usd": budget,
                "actual_costs": {"verifier": {"cost_usd": total_cost}},
                "total_cost_usd": total_cost,
                "budget_utilization_pct": (total_cost / budget) * 100.0,
                "g5_triggered": False,
                "editor_decision": None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _patch_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(audit_budget, "COST_TRACKING_DIR", tmp_path / "cost_tracking")
    monkeypatch.setattr(g5_gate, "DATA_DIR", tmp_path / "cost_tracking")


def test_check_below_threshold_no_trigger(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-low", total_cost=1.0, budget=1.0)
    result = g5_gate.check_and_notify("art-low")
    assert result["g5_triggered"] is False


def test_check_above_threshold_triggers_g5(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-high", total_cost=1.6, budget=1.0)
    result = g5_gate.check_and_notify("art-high")
    assert result["g5_triggered"] is True
    assert result["action_required"] == "editor_decision"


def test_apply_continue_unblocks_pipeline(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-continue", total_cost=1.6, budget=1.0)
    result = g5_gate.apply_decision("art-continue", "continue")
    assert result["status"] == "approved"
    updated = audit_budget.read_article_cost("art-continue")
    assert updated["editor_decision"] == "continue"
    assert updated["estimated_budget_usd"] == 2.0


def test_apply_continue_is_idempotent(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-idempotent", total_cost=1.6, budget=1.0)
    g5_gate.apply_decision("art-idempotent", "continue")
    second = g5_gate.apply_decision("art-idempotent", "continue")
    assert second["approved_budget_usd"] == 2.0
    updated = audit_budget.read_article_cost("art-idempotent")
    assert updated["estimated_budget_usd"] == 2.0


def test_apply_abort_marks_killed(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-abort", total_cost=1.6, budget=1.0)
    result = g5_gate.apply_decision("art-abort", "abort")
    assert result["status"] == "killed"


def test_apply_downgrade_changes_model_to_haiku(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-down", total_cost=1.6, budget=1.0)
    result = g5_gate.apply_decision("art-down", "downgrade")
    assert result["model_override"] == "haiku"
    updated = audit_budget.read_article_cost("art-down")
    assert updated["model_override"] == "haiku"


def test_slack_notification_payload(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-slack", total_cost=1.6, budget=1.0)
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example/test")
    captured: dict[str, object] = {}

    class FakeRequests:
        @staticmethod
        def post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout

    monkeypatch.setitem(sys.modules, "requests", FakeRequests)
    result = g5_gate.check_and_notify("art-slack")
    assert result["slack_notified"] is True
    assert captured["timeout"] == 10
    assert "Current cost" in captured["json"]["blocks"][0]["text"]["text"]


def test_sla_deadline_30_minutes(tmp_path, monkeypatch):
    _patch_dirs(tmp_path, monkeypatch)
    _write_article_cost(tmp_path, "art-sla", total_cost=1.6, budget=1.0)
    result = g5_gate.check_and_notify("art-sla")
    deadline = datetime.fromisoformat(result["sla_deadline"])
    delta = deadline - datetime.now(timezone.utc)
    assert 1700 <= delta.total_seconds() <= 1900
