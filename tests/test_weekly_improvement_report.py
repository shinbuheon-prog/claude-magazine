from __future__ import annotations

import importlib.util
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
