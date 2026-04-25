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


# ─────────────────────────────────────────────────────────────────────────────
# 추가 커버리지 — Round 1 직접 구현 (Phase 8 closure 후)
# ─────────────────────────────────────────────────────────────────────────────


def test_scrub_redacts_emails_keys_bearer_envs() -> None:
    """_scrub: 이메일·API key·bearer token·env var 패턴 마스킹."""
    text = "contact me at editor@example.com bearer abcdefghij1234 sk-ant-secret_abcdefghij1 ANTHROPIC_API_KEY=secret123"
    result = failure_collector._scrub(text)
    assert "<email>" in result
    assert "bearer <token>" in result
    assert "<api-key>" in result
    assert "ANTHROPIC_API_KEY=<redacted>" in result


def test_scrub_recurses_into_dict_and_list() -> None:
    """_scrub: 중첩 dict·list 재귀 처리."""
    payload = {
        "email": "x@y.com",
        "items": ["bearer abcdefghij1234", "safe text"],
        "nested": {"key": "sk-ant-key_abcdefghij2"},
        "number": 42,
        "none": None,
    }
    result = failure_collector._scrub(payload)
    assert result["email"] == "<email>"
    assert "bearer <token>" in result["items"][0]
    assert result["items"][1] == "safe text"
    assert "<api-key>" in result["nested"]["key"]
    assert result["number"] == 42
    assert result["none"] is None


def test_collect_log_failures_aggregates_lint_and_factcheck() -> None:
    """collect_log_failures: editorial_lint items[fail] 집계 + factcheck request_id 수집."""
    tmp_path, monkeypatch = _workspace("task055_loglogs")
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    try:
        monkeypatch.setattr(failure_collector, "LOGS_DIR", logs_dir)
        # 최근 timestamp로 cutoff 통과
        recent_ts = "2026-04-25T09:00:00+00:00"
        _write_json(
            logs_dir / "lint_a_20260425_090000.json",
            {
                "timestamp": recent_ts,
                "items": [
                    {"id": "source-id", "status": "fail", "message": "missing src token"},
                    {"id": "ai-disclosure", "status": "fail", "message": "no AI notice"},
                    {"id": "image-rights", "status": "pass", "message": "ok"},
                ],
            },
        )
        _write_json(
            logs_dir / "lint_b_20260425_100000.json",
            {
                "timestamp": recent_ts,
                "items": [
                    {"id": "source-id", "status": "fail", "message": "still missing"},
                ],
            },
        )
        _write_json(
            logs_dir / "factcheck_20260425_110000.json",
            {"timestamp": recent_ts, "request_id": "req-abc-001"},
        )
        _write_json(
            logs_dir / "factcheck_20260425_120000.json",
            {"timestamp": recent_ts, "request_id": "req-abc-002"},
        )

        result = failure_collector.collect_log_failures(7)
        assert result["factcheck_summary"]["total_runs"] == 2
        assert "req-abc-001" in result["factcheck_summary"]["sample_request_ids"]
        # source-id가 가장 많이 fail — 첫 번째에 있어야 함
        check_ids = [entry["check_id"] for entry in result["editorial_lint_failures"]]
        assert check_ids[0] == "source-id"
        # source-id count 2
        assert result["editorial_lint_failures"][0]["count"] == 2
    finally:
        _cleanup(tmp_path, monkeypatch)


def test_collect_log_failures_returns_empty_when_logs_dir_missing() -> None:
    """LOGS_DIR 부재 시 빈 결과 반환."""
    tmp_path, monkeypatch = _workspace("task055_emptylogs")
    try:
        monkeypatch.setattr(failure_collector, "LOGS_DIR", tmp_path / "nonexistent")
        result = failure_collector.collect_log_failures(7)
        assert result["editorial_lint_failures"] == []
        assert result["factcheck_summary"] == {}
    finally:
        _cleanup(tmp_path, monkeypatch)


def test_collect_editor_corrections_returns_empty_when_db_missing() -> None:
    """CORRECTIONS_DB 파일 없으면 빈 list 반환."""
    tmp_path, monkeypatch = _workspace("task055_nodb")
    try:
        monkeypatch.setattr(failure_collector, "CORRECTIONS_DB", tmp_path / "nonexistent.db")
        result = failure_collector.collect_editor_corrections(7)
        assert result == []
    finally:
        _cleanup(tmp_path, monkeypatch)


def test_collect_editor_corrections_aggregates_by_type() -> None:
    """SQLite editor_corrections.db에서 type별 집계 + severity·category 분포."""
    import sqlite3
    tmp_path, monkeypatch = _workspace("task055_db")
    db_path = tmp_path / "editor_corrections.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE corrections (
                correction_type TEXT,
                severity TEXT,
                category TEXT,
                original_text TEXT,
                corrected_text TEXT,
                editor_note TEXT,
                timestamp TEXT
            )
        """)
        recent = "2026-04-25T09:00:00+00:00"
        rows = [
            ("typo", "low", "punctuation", "안녕하세여", "안녕하세요", "맞춤법", recent),
            ("typo", "low", "punctuation", "되다", "돼다 - 수정", "tense", recent),
            ("source_id", "high", "citation", "원문 인용", "[src-001] 원문 인용", "출처 연결", recent),
        ]
        conn.executemany(
            "INSERT INTO corrections VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    try:
        monkeypatch.setattr(failure_collector, "CORRECTIONS_DB", db_path)
        result = failure_collector.collect_editor_corrections(7)
        # typo 2건, source_id 1건 → typo가 first
        assert result[0]["type"] == "typo"
        assert result[0]["count"] == 2
        assert result[1]["type"] == "source_id"
        assert result[1]["severity_high_count"] == 1
    finally:
        _cleanup(tmp_path, monkeypatch)


def test_collect_standards_failures_aggregates_by_rule() -> None:
    """standards_checker 결과 로그에서 fail rule_id별 집계."""
    tmp_path, monkeypatch = _workspace("task055_stand")
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    try:
        monkeypatch.setattr(failure_collector, "LOGS_DIR", logs_dir)
        recent_ts = "2026-04-25T09:00:00+00:00"
        _write_json(
            logs_dir / "standards_a_20260425_090000.json",
            {
                "timestamp": recent_ts,
                "category": "feature",
                "common_checks": [
                    {"id": "min_word_count", "status": "fail", "rule": "min 800 words", "measured": "720", "expected": "800"},
                ],
                "category_checks": [
                    {"id": "must_have_quote", "status": "fail", "rule": "1+ quote", "measured": "0", "expected": "1"},
                ],
                "should_checks": [
                    {"id": "subhead_count", "status": "pass"},
                ],
            },
        )
        _write_json(
            logs_dir / "standards_b_20260425_100000.json",
            {
                "timestamp": recent_ts,
                "category": "deep_dive",
                "common_checks": [
                    {"id": "min_word_count", "status": "fail", "rule": "min 800 words", "measured": "650", "expected": "800"},
                ],
            },
        )

        result = failure_collector.collect_standards_failures(7)
        rule_ids = [item["rule_id"] for item in result]
        assert "min_word_count" in rule_ids
        # min_word_count는 2건, 카테고리 분산 (feature·deep_dive)
        wc = next(item for item in result if item["rule_id"] == "min_word_count")
        assert wc["count"] == 2
        # examples include rule/measured/expected
        assert wc["examples"][0]["rule"] == "min 800 words"
    finally:
        _cleanup(tmp_path, monkeypatch)


def test_collect_ghost_publications_returns_zero_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """GHOST_CONTENT_API_URL·KEY 미설정 시 0 반환."""
    monkeypatch.delenv("GHOST_CONTENT_API_URL", raising=False)
    monkeypatch.delenv("GHOST_API_URL", raising=False)
    monkeypatch.delenv("GHOST_CONTENT_API_KEY", raising=False)
    assert failure_collector.collect_ghost_publications(7) == 0


def test_helpers_parse_iso8601_and_safe_read_json(tmp_path: Path) -> None:
    """헬퍼 함수 — ISO8601·JSON 안전 파싱·파일 timestamp 추출."""
    # ISO8601 파싱
    assert failure_collector._parse_iso8601(None) is None
    assert failure_collector._parse_iso8601("") is None
    assert failure_collector._parse_iso8601("invalid") is None
    parsed = failure_collector._parse_iso8601("2026-04-25T09:00:00Z")
    assert parsed is not None and parsed.tzinfo is not None
    naive = failure_collector._parse_iso8601("2026-04-25T09:00:00")
    assert naive is not None and naive.tzinfo is not None

    # _safe_read_json
    valid = tmp_path / "valid.json"
    valid.write_text('{"key": "value"}', encoding="utf-8")
    assert failure_collector._safe_read_json(valid) == {"key": "value"}

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    assert failure_collector._safe_read_json(invalid) is None

    not_dict = tmp_path / "list.json"
    not_dict.write_text("[1,2,3]", encoding="utf-8")
    assert failure_collector._safe_read_json(not_dict) is None

    # _log_file_timestamp — 파일명 패턴 + mtime fallback
    ts_in_name = tmp_path / "log_20260425_090000.json"
    ts_in_name.write_text("{}", encoding="utf-8")
    parsed_ts = failure_collector._log_file_timestamp(ts_in_name)
    assert parsed_ts is not None
    assert parsed_ts.year == 2026

    # 파일명에 timestamp 없으면 mtime 사용 (fallback)
    plain = tmp_path / "plain.json"
    plain.write_text("{}", encoding="utf-8")
    fallback_ts = failure_collector._log_file_timestamp(plain)
    assert fallback_ts is not None  # mtime이 있으므로


def test_signed_percent_text() -> None:
    """_signed_percent_text: None·실수 포맷."""
    assert failure_collector._signed_percent_text(None) == "n/a"
    assert failure_collector._signed_percent_text(0.0) == "+0%"
    assert failure_collector._signed_percent_text(15.4) == "+15%"
    assert failure_collector._signed_percent_text(-23.7) == "-24%"


def test_collect_failures_full_aggregation() -> None:
    """collect_failures: 7 섹션 전체가 dict로 반환되는지 확인."""
    tmp_path, monkeypatch = _workspace("task055_full")
    logs_dir = tmp_path / "logs"
    reports_dir = tmp_path / "reports"
    logs_dir.mkdir()
    reports_dir.mkdir()
    try:
        monkeypatch.setattr(failure_collector, "LOGS_DIR", logs_dir)
        monkeypatch.setattr(failure_collector, "REPORTS_DIR", reports_dir)
        monkeypatch.setattr(failure_collector, "CORRECTIONS_DB", tmp_path / "noop.db")
        result = failure_collector.collect_failures(since_days=7)
        # 모든 신구 섹션 키 존재
        for key in [
            "period",
            "editorial_lint_failures",
            "factcheck_summary",
            "standards_failures",
            "editor_corrections",
            "langfuse_anomalies",
            "total_articles",
            "cache_signals",
            "citations_signals",
            "illustration_signals",
            "publish_monthly_signals",
        ]:
            assert key in result, f"missing section: {key}"
        # period 정상
        assert "from" in result["period"]
        assert "to" in result["period"]
        assert result["period"]["days"] == 7
    finally:
        _cleanup(tmp_path, monkeypatch)
