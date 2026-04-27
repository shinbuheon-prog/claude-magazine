from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipeline import g2_gate


def _write_factcheck_log(tmp_path: Path, article_id: str, summary: dict) -> None:
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    (logs_dir / f"factcheck_{article_id}.json").write_text(
        json.dumps({"article_id": article_id, "verdict_summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_pass_when_ratio_above_085(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    _write_factcheck_log(tmp_path, "art-pass", {"confirmed_ratio": 0.91, "recommendation": "proceed", "critical_issues": []})
    result = g2_gate.evaluate("art-pass")
    assert result["decision"] == "pass"


def test_g2_review_when_ratio_between_05_and_085(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    _write_factcheck_log(tmp_path, "art-review", {"confirmed_ratio": 0.78, "recommendation": "revise", "critical_issues": []})
    result = g2_gate.evaluate("art-review")
    assert result["decision"] == "g2_review"


def test_block_when_ratio_below_05(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    _write_factcheck_log(tmp_path, "art-block", {"confirmed_ratio": 0.32, "recommendation": "kill", "critical_issues": ["bad claim"]})
    result = g2_gate.evaluate("art-block")
    assert result["decision"] == "block"


def test_slack_notification_payload_format(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    _write_factcheck_log(tmp_path, "art-slack", {"confirmed_ratio": 0.78, "recommendation": "revise", "critical_issues": []})
    monkeypatch.setenv("NOTIFY_SLACK_WEBHOOK", "https://hooks.example/test")
    captured: dict[str, object] = {}

    class FakeRequests:
        @staticmethod
        def post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout

    monkeypatch.setitem(sys.modules, "requests", FakeRequests)
    result = g2_gate.evaluate("art-slack")
    assert result["slack_notified"] is True
    assert captured["url"] == "https://hooks.example/test"
    assert captured["timeout"] == 10
    body = captured["json"]
    assert "Confirmed ratio" in body["blocks"][0]["text"]["text"]


def test_email_notification_queue_created(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(g2_gate, "QUEUE_DIR", tmp_path / "queue")
    _write_factcheck_log(tmp_path, "art-email", {"confirmed_ratio": 0.78, "recommendation": "revise", "critical_issues": []})
    monkeypatch.setenv("NOTIFY_EMAIL", "editor@example.com")
    result = g2_gate.evaluate("art-email")
    assert result["email_notified"] is True
    assert (tmp_path / "queue" / "g2_art-email.json").exists()


def test_strict_exit_codes(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    _write_factcheck_log(tmp_path, "art-pass", {"confirmed_ratio": 0.90, "recommendation": "proceed", "critical_issues": []})
    _write_factcheck_log(tmp_path, "art-review", {"confirmed_ratio": 0.70, "recommendation": "revise", "critical_issues": []})
    _write_factcheck_log(tmp_path, "art-block", {"confirmed_ratio": 0.40, "recommendation": "kill", "critical_issues": []})
    assert g2_gate.main(["--article-id", "art-pass", "--strict"]) == 0
    assert g2_gate.main(["--article-id", "art-review", "--strict"]) == 1
    assert g2_gate.main(["--article-id", "art-block", "--strict"]) == 2


def test_sla_deadline_2h_from_now(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "LOGS_DIR", tmp_path / "logs")
    _write_factcheck_log(tmp_path, "art-sla", {"confirmed_ratio": 0.75, "recommendation": "revise", "critical_issues": []})
    result = g2_gate.evaluate("art-sla")
    deadline = datetime.fromisoformat(result["sla_deadline"])
    delta = deadline - datetime.now(timezone.utc)
    assert 7100 <= delta.total_seconds() <= 7300


def test_factcheck_log_fallback_for_legacy_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(g2_gate, "QUEUE_DIR", tmp_path / "queue")
    log_path = tmp_path / "factcheck_legacy.json"
    log_path.write_text(
        json.dumps({"verdict_summary": {"confirmed_ratio": 0.74, "recommendation": "revise", "critical_issues": []}}, ensure_ascii=False),
        encoding="utf-8",
    )
    result = g2_gate.evaluate(None, factcheck_log=str(log_path))
    assert result["article_id"] == "legacy"
    assert result["decision"] == "g2_review"
