from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from pipeline import failure_collector


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _workspace(name: str) -> tuple[Path, pytest.MonkeyPatch]:
    root = Path(tempfile.mkdtemp(prefix=f"{name}_", dir=str(Path.home())))
    monkeypatch = pytest.MonkeyPatch()
    return root, monkeypatch


def _cleanup(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()
    shutil.rmtree(root, ignore_errors=True)


@pytest.mark.integration
def test_collect_operational_signals() -> None:
    tmp_path, monkeypatch = _workspace("task053_case1")
    logs_dir = tmp_path / "logs"
    reports_dir = tmp_path / "reports"
    data_dir = tmp_path / "data"
    logs_dir.mkdir()
    reports_dir.mkdir()
    data_dir.mkdir()

    try:
        monkeypatch.setattr(failure_collector, "LOGS_DIR", logs_dir)
        monkeypatch.setattr(failure_collector, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(failure_collector, "CORRECTIONS_DB", data_dir / "editor_corrections.db")
        monkeypatch.setenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "10")

        _write_json(
            logs_dir / "factcheck_20260412_090000.json",
            {
                "timestamp": "2026-04-12T09:00:00+00:00",
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 90,
                "cache_enabled": True,
            },
        )
        _write_json(
            logs_dir / "factcheck_20260413_090000.json",
            {
                "timestamp": "2026-04-13T09:00:00+00:00",
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 90,
                "cache_enabled": True,
            },
        )
        _write_json(
            logs_dir / "factcheck_20260422_090000.json",
            {
                "timestamp": "2026-04-22T09:00:00+00:00",
                "cache_creation_input_tokens": 90,
                "cache_read_input_tokens": 10,
                "cache_enabled": True,
            },
        )
        _write_json(
            logs_dir / "factcheck_20260423_090000.json",
            {
                "timestamp": "2026-04-23T09:00:00+00:00",
                "cache_creation_input_tokens": 90,
                "cache_read_input_tokens": 10,
                "cache_enabled": True,
            },
        )
        _write_json(
            logs_dir / "brief_20260423_090000.json",
            {
                "timestamp": "2026-04-23T09:00:00+00:00",
                "cache_enabled": True,
            },
        )

        _write_json(
            logs_dir / "lint_article_a_20260412_090000.json",
            {
                "timestamp": "2026-04-12T09:00:00+00:00",
                "article_id": "art-a",
                "items": [{"id": "citations-cross-check", "status": "pass", "message": "ok"}],
            },
        )
        _write_json(
            logs_dir / "lint_article_b_20260422_090000.json",
            {
                "timestamp": "2026-04-22T09:00:00+00:00",
                "article_id": "art-b",
                "items": [{"id": "citations-cross-check", "status": "warn", "message": "manual source_id not backed by citations"}],
            },
        )
        _write_json(
            logs_dir / "lint_article_c_20260423_090000.json",
            {
                "timestamp": "2026-04-23T09:00:00+00:00",
                "article_id": "art-c",
                "items": [{"id": "citations-cross-check", "status": "warn", "message": "manual source_id not backed by citations"}],
            },
        )

        (logs_dir / "illustrations.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "timestamp": "2026-04-22T09:00:00+00:00",
                            "provider": "pollinations",
                            "cost_estimate": 2.0,
                            "provider_chain": ["pollinations"],
                            "provider_context": {"requested_provider": "pollinations"},
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-04-23T09:00:00+00:00",
                            "provider": "placeholder",
                            "cost_estimate": 3.0,
                            "provider_chain": ["pollinations", "placeholder"],
                            "provider_context": {"requested_provider": "pollinations", "failure_reason": "rate limit"},
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-04-24T09:00:00+00:00",
                            "provider": "placeholder",
                            "cost_estimate": 4.0,
                            "provider_chain": ["pollinations", "placeholder"],
                            "provider_context": {"requested_provider": "pollinations", "failure_reason": "timeout"},
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

        _write_json(
            reports_dir / "publish_state_2026-04.json",
            {
                "month": "2026-04",
                "last_updated": "2026-04-20T09:00:00+00:00",
                "telemetry": {"pdf_compile": {"duration_sec": 10, "cost_usd": None}},
            },
        )
        _write_json(
            reports_dir / "publish_state_2026-05.json",
            {
                "month": "2026-05",
                "last_updated": "2026-04-24T09:00:00+00:00",
                "telemetry": {"pdf_compile": {"duration_sec": 20, "cost_usd": None}},
            },
        )

        cache = failure_collector.collect_cache_signals(14)
        assert cache["pipelines"]["fact_checker"]["anomaly"] == "degrading"

        citations = failure_collector.collect_citations_signals(14)
        assert citations["anomaly"] == "mismatch_rising"
        assert citations["top_mismatched_article_ids"][:2] == ["art-b", "art-c"]

        illustration = failure_collector.collect_illustration_signals(14)
        assert illustration["anomaly"] == "budget_approaching"
        assert illustration["fallback_reasons"]["rate_limit"] == 1
        assert illustration["fallback_reasons"]["timeout"] == 1

        publish = failure_collector.collect_publish_monthly_signals(14)
        assert publish["bottleneck_stage"] == "pdf_compile"
        assert publish["anomaly"] == "bottleneck_worsening"

        failures = failure_collector.collect_failures(14)
        assert "cache_signals" in failures
        assert "citations_signals" in failures
        assert "illustration_signals" in failures
        assert "publish_monthly_signals" in failures
    finally:
        _cleanup(tmp_path, monkeypatch)


@pytest.mark.integration
def test_collect_operational_signals_insufficient_data() -> None:
    tmp_path, monkeypatch = _workspace("task053_case2")
    logs_dir = tmp_path / "logs"
    reports_dir = tmp_path / "reports"
    logs_dir.mkdir()
    reports_dir.mkdir()

    try:
        monkeypatch.setattr(failure_collector, "LOGS_DIR", logs_dir)
        monkeypatch.setattr(failure_collector, "REPORTS_DIR", reports_dir)
        monkeypatch.setenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "0")

        cache = failure_collector.collect_cache_signals(7)
        assert cache["pipelines"]["fact_checker"]["anomaly"] == "insufficient_data"

        citations = failure_collector.collect_citations_signals(7)
        assert citations["anomaly"] == "insufficient_data"

        illustration = failure_collector.collect_illustration_signals(7)
        assert illustration["anomaly"] == "insufficient_data"

        publish = failure_collector.collect_publish_monthly_signals(7)
        assert publish["anomaly"] == "insufficient_data"
    finally:
        _cleanup(tmp_path, monkeypatch)
