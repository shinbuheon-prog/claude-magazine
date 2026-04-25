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


# ─────────────────────────────────────────────────────────────────────────────
# 추가 커버리지 — Round 1 직접 구현
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_json_from_fenced_code_block() -> None:
    """Opus 응답이 fenced code block(```json ...```)일 때 JSON 추출."""
    raw = '여기 결과입니다.\n```json\n{"patterns": [{"pattern": "x"}], "confidence": 0.7}\n```\n끝.'
    parsed = sop_updater._extract_json(raw)
    assert parsed["confidence"] == 0.7
    assert parsed["patterns"][0]["pattern"] == "x"


def test_extract_json_from_unfenced_text() -> None:
    """fence 없이 dictionary로 시작하는 평문 응답에서도 JSON 영역만 추출."""
    raw = '응답 시작\n{"patterns": [], "confidence": 0.3}\n응답 끝'
    parsed = sop_updater._extract_json(raw)
    assert parsed["confidence"] == 0.3


def test_extract_json_returns_empty_on_invalid() -> None:
    """JSON 파싱 실패 시 빈 dict 반환 — 안전 fallback."""
    assert sop_updater._extract_json("") == {}
    assert sop_updater._extract_json("not json at all") == {}
    assert sop_updater._extract_json('{"unclosed": ') == {}


def test_empty_response_schema() -> None:
    """_empty_response: 빈 응답이지만 스키마 일관성 유지."""
    result = sop_updater._empty_response("test reason")
    assert result["patterns"] == []
    assert result["proposed_updates"] == []
    assert result["opus_request_id"] is None
    assert result["confidence"] == 0.0
    assert result["notes"] == "test reason"


def test_analyze_and_propose_returns_empty_when_api_key_missing(monkeypatch) -> None:
    """ANTHROPIC_API_KEY 미설정 + provider=api → empty response (call 안 함)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_PROVIDER", "api")
    result = sop_updater.analyze_and_propose({"period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7}})
    assert result["opus_request_id"] is None
    assert result["confidence"] == 0.0
    assert "ANTHROPIC_API_KEY missing" in result["notes"]


def test_analyze_and_propose_with_mock_provider(monkeypatch, tmp_path) -> None:
    """Mock provider 설정 시 정상 흐름 — _log_request·payload 정합."""
    monkeypatch.setenv("CLAUDE_PROVIDER", "mock")  # api 검증 우회
    monkeypatch.setattr(sop_updater, "LOGS_DIR", tmp_path)

    class _MockResult:
        request_id = "req-test-001"
        text = '```json\n{"patterns": [{"pattern": "p1"}], "proposed_updates": [], "confidence": 0.85, "notes": "mock"}\n```'
        input_tokens = 100
        output_tokens = 50

    class _MockProvider:
        def stream_complete(self, **_):
            return _MockResult()

    def fake_get_provider():
        return _MockProvider()

    monkeypatch.setattr("pipeline.claude_provider.get_provider", fake_get_provider, raising=False)

    failures = {"period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7}}
    result = sop_updater.analyze_and_propose(failures)

    assert result["opus_request_id"] == "req-test-001"
    assert result["confidence"] == 0.85
    assert len(result["patterns"]) == 1
    assert result["usage"]["input_tokens"] == 100

    # log file 작성 확인
    log_files = list(tmp_path.glob("sop_update_*.json"))
    assert len(log_files) == 1


def test_analyze_and_propose_handles_provider_failure(monkeypatch, tmp_path) -> None:
    """provider 호출 실패 (모든 attempts) → empty_response."""
    monkeypatch.setenv("CLAUDE_PROVIDER", "mock")
    monkeypatch.setattr(sop_updater, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(sop_updater, "MAX_RETRIES", 1)
    monkeypatch.setattr(sop_updater, "RETRY_WAIT_SECONDS", 0)

    class _FailingProvider:
        def stream_complete(self, **_):
            raise RuntimeError("provider exploded")

    monkeypatch.setattr("pipeline.claude_provider.get_provider", lambda: _FailingProvider(), raising=False)

    result = sop_updater.analyze_and_propose({"period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7}})
    assert result["opus_request_id"] is None
    assert "call failed" in result["notes"]


def test_analyze_and_propose_handles_invalid_json(monkeypatch, tmp_path) -> None:
    """Opus 응답이 JSON 아닐 때 empty_response + log 작성."""
    monkeypatch.setenv("CLAUDE_PROVIDER", "mock")
    monkeypatch.setattr(sop_updater, "LOGS_DIR", tmp_path)

    class _NonJsonResult:
        request_id = "req-no-json"
        text = "Sorry, I cannot produce JSON right now."
        input_tokens = 50
        output_tokens = 20

    class _Provider:
        def stream_complete(self, **_):
            return _NonJsonResult()

    monkeypatch.setattr("pipeline.claude_provider.get_provider", lambda: _Provider(), raising=False)

    result = sop_updater.analyze_and_propose({"period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7}})
    assert result["opus_request_id"] is None
    assert "not valid JSON" in result["notes"]
    # log file 여전히 생성됨 (empty 기록용)
    log_files = list(tmp_path.glob("sop_update_*.json"))
    assert len(log_files) == 1


def test_analyze_and_propose_clamps_confidence(monkeypatch, tmp_path) -> None:
    """confidence가 1.0 초과·음수일 때 0.0~1.0 clamp."""
    monkeypatch.setenv("CLAUDE_PROVIDER", "mock")
    monkeypatch.setattr(sop_updater, "LOGS_DIR", tmp_path)

    class _OverConfident:
        request_id = "req-clamp"
        text = '{"patterns": [], "proposed_updates": [], "confidence": 5.0, "notes": ""}'
        input_tokens = 0
        output_tokens = 0

    monkeypatch.setattr("pipeline.claude_provider.get_provider", lambda: type("P", (), {"stream_complete": lambda self, **_: _OverConfident()})(), raising=False)
    result = sop_updater.analyze_and_propose({"period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7}})
    assert result["confidence"] == 1.0


def test_summarize_failures_truncates_long_input() -> None:
    """매우 큰 failures dict → limit_chars 절삭."""
    huge_failures = {
        "period": {"from": "2026-04-18", "to": "2026-04-25", "days": 7},
        "editorial_lint_failures": [
            {"check_id": f"check_{i}", "count": i, "examples": [{"file": f"f{i}.json", "message": "x" * 500}]}
            for i in range(50)
        ],
    }
    summary = sop_updater._summarize_failures(huge_failures, limit_chars=2000)
    assert len(summary) <= 2000


def test_smoke_test_runs_without_api_key(monkeypatch) -> None:
    """_smoke_test: API 키 없어도 empty 응답으로 통과."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLAUDE_PROVIDER", "api")
    # smoke_test는 print를 호출하므로 stdout만 캡처되면 OK — 예외 없으면 통과
    sop_updater._smoke_test()
