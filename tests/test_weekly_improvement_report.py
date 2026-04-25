from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_weekly_improvement() -> object:
    path = Path(__file__).resolve().parents[1] / "scripts" / "weekly_improvement.py"
    spec = importlib.util.spec_from_file_location("weekly_improvement_test_module_task053", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_weekly_report_renders_operational_summary() -> None:
    weekly_improvement = _load_weekly_improvement()
    failures = {
        "period": {"from": "2026-04-18T00:00:00+00:00", "to": "2026-04-25T00:00:00+00:00", "days": 7},
        "total_articles": 2,
        "editorial_lint_failures": [],
        "editor_corrections": [],
        "langfuse_anomalies": [],
        "standards_failures": [],
        "cache_signals": {"pipelines": {"fact_checker": {"runs": 4, "cache_enabled_runs": 4, "hit_rate_change_7d": -0.15, "anomaly": "stable"}}},
        "citations_signals": {"checks_total": 3, "by_status": {"pass": 1, "warn-mismatch": 2}, "anomaly": "mismatch_rising"},
        "illustration_signals": {"provider_distribution": {"placeholder": 2}, "fallback_rate": 0.5, "budget_utilization": 0.0, "anomaly": "fallback_rising"},
        "publish_monthly_signals": {"bottleneck_stage": "pdf_compile", "stage_duration_change_7d": {"pdf_compile": "+18%"}, "anomaly": "bottleneck_worsening"},
    }
    proposal = {"patterns": [], "proposed_updates": [], "opus_request_id": None, "confidence": 0.0, "notes": "dry-run"}

    report = weekly_improvement.render_report(failures, proposal, "2026-04-18 ~ 2026-04-25")
    assert "Operational Signals (TASK_053)" in report
    assert "fact_checker runs=4" in report
    assert "bottleneck_stage=pdf_compile" in report
    assert "[OPERATIONS] cache anomaly" in report


def test_weekly_report_renders_repeat_failure_queue() -> None:
    weekly_improvement = _load_weekly_improvement()
    failures = {
        "period": {"from": "2026-04-18T00:00:00+00:00", "to": "2026-04-25T00:00:00+00:00", "days": 7},
        "total_articles": 1,
        "editorial_lint_failures": [],
        "editor_corrections": [],
        "langfuse_anomalies": [],
        "standards_failures": [],
        "cache_signals": {},
        "citations_signals": {},
        "illustration_signals": {},
        "publish_monthly_signals": {},
        "repeat_failure_queue": [
            {
                "window_days": 14,
                "repeats": [
                    {"class": "puppeteer_timeout", "count": 4, "stages": ["pdf_compile"]},
                ],
            }
        ],
    }
    proposal = {"patterns": [], "proposed_updates": [], "opus_request_id": None, "confidence": 0.0, "notes": "dry-run"}

    report = weekly_improvement.render_report(failures, proposal, "2026-04-18 ~ 2026-04-25")
    assert "Priority Queue (Repeated Failures)" in report
    assert "puppeteer_timeout" in report
    assert "[PRIORITY] repeated failure `puppeteer_timeout` (4x) triaged" in report


def test_weekly_run_archives_repeat_failure_queue(tmp_path: Path, monkeypatch) -> None:
    weekly_improvement = _load_weekly_improvement()
    reports_dir = tmp_path / "reports"
    queue_dir = reports_dir / "auto_trigger_queue"
    queue_dir.mkdir(parents=True)
    marker_path = queue_dir / "2026-04-25_test.json"
    marker_path.write_text(
        json.dumps(
            {
                "created_at": "2026-04-25T00:00:00+00:00",
                "window_days": 14,
                "threshold": 3,
                "status": "queued",
                "repeats": [{"class": "puppeteer_timeout", "count": 3, "stages": ["pdf_compile"]}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(weekly_improvement, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(
        weekly_improvement,
        "collect_failures",
        lambda since_days: {
            "period": {"from": "2026-04-18T00:00:00+00:00", "to": "2026-04-25T00:00:00+00:00", "days": since_days},
            "total_articles": 0,
            "editorial_lint_failures": [],
            "editor_corrections": [],
            "langfuse_anomalies": [],
            "standards_failures": [],
            "cache_signals": {},
            "citations_signals": {},
            "illustration_signals": {},
            "publish_monthly_signals": {},
        },
    )
    monkeypatch.setattr(
        weekly_improvement,
        "analyze_and_propose",
        lambda failures: {"patterns": [], "proposed_updates": [], "opus_request_id": None, "confidence": 0.0, "notes": "ok"},
    )
    output = reports_dir / "improvement_test.md"
    assert weekly_improvement.run(since_days=7, output=output, dry_run=False, create_issue=False) == 0
    assert output.exists()
    archived = queue_dir / "archived" / marker_path.name
    assert archived.exists()
    assert not marker_path.exists()
