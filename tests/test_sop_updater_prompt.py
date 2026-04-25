from __future__ import annotations

from pipeline import sop_updater


def test_sop_summary_includes_operational_sections() -> None:
    summary = sop_updater._summarize_failures(
        {
            "period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7},
            "cache_signals": {"pipelines": {"fact_checker": {"runs": 4, "cache_enabled_runs": 4, "hit_rate_change_7d": -0.3, "anomaly": "degrading"}}},
            "citations_signals": {"checks_total": 4, "by_status": {"warn-mismatch": 2}, "top_mismatched_article_ids": ["art-a"], "anomaly": "mismatch_rising"},
            "illustration_signals": {"provider_distribution": {"placeholder": 2}, "fallback_rate": 0.4, "budget_utilization": 0.9, "fallback_reasons": {"timeout": 1}, "anomaly": "budget_approaching"},
            "publish_monthly_signals": {"recent_runs": [{"month": "2026-05"}], "bottleneck_stage": "pdf_compile", "stage_duration_change_7d": {"pdf_compile": "+20%"}, "anomaly": "bottleneck_worsening"},
        }
    )
    assert "cache_signals" in summary
    assert "citations_signals" in summary
    assert "illustration_signals" in summary
    assert "publish_monthly_signals" in summary


def test_sop_system_prompt_mentions_operations() -> None:
    assert "operations:<topic>" in sop_updater.SYSTEM_PROMPT
    assert "cache, citations, illustration, and publish" in sop_updater.SYSTEM_PROMPT
