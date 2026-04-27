from __future__ import annotations

import json
from pathlib import Path

from pipeline import quality_review


class FakeProvider:
    def __init__(self, payload: dict):
        self.payload = payload

    def stream_complete(self, system, user, model_tier="opus", max_tokens=0, stream_callback=None):
        return type(
            "Result",
            (),
            {
                "text": json.dumps(self.payload, ensure_ascii=False),
                "request_id": "req-quality",
                "input_tokens": 100,
                "output_tokens": 50,
            },
        )()


class NoCallProvider:
    def stream_complete(self, *args, **kwargs):
        raise AssertionError("dry-run should not call provider")


def _draft(tmp_path: Path) -> Path:
    path = tmp_path / "draft.md"
    path.write_text("# Draft\n\n본문", encoding="utf-8")
    return path


def _criteria(scores: list[int]) -> list[dict]:
    return [
        {
            "id": idx,
            "criterion": f"criterion {idx}",
            "score": score,
            "comment": "ok" if score >= 4 else "fix",
            "fix_suggestion": None if score >= 4 else "tighten",
        }
        for idx, score in enumerate(scores, start=1)
    ]


def test_pass_all_13_criteria(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria([5] * 13), "priority_fixes": [], "improved_body": "body"}))
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-pass")
    assert result["verdict"] == "pass"
    assert result["publishable"] is True


def test_partial_with_3_fixes(tmp_path, monkeypatch):
    scores = [3, 3, 3] + [5] * 10
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(
        quality_review,
        "get_provider",
        lambda: FakeProvider(
            {
                "criteria_scores": _criteria(scores),
                "priority_fixes": [{"location": "sec1", "problem": "p", "recommended_fix": "f"}] * 3,
                "improved_body": "body",
            }
        ),
    )
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-partial")
    assert result["verdict"] == "partial"
    assert len(result["priority_fixes"]) == 3


def test_fail_below_9_criteria(tmp_path, monkeypatch):
    scores = [5] * 8 + [3] * 5
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria(scores), "priority_fixes": [], "improved_body": "body"}))
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-fail")
    assert result["verdict"] == "fail"


def test_sponsored_extra_checks(tmp_path, monkeypatch):
    scores = [5] * 11 + [3, 5]
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria(scores), "priority_fixes": [], "improved_body": "body"}))
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-sponsored", is_sponsored=True)
    assert result["verdict"] == "fail"
    assert any("Sponsored" in fix["recommended_fix"] for fix in result["priority_fixes"])


def test_request_id_saved(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    monkeypatch.setattr(quality_review, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria([5] * 13), "priority_fixes": [], "improved_body": "body"}))
    quality_review.review_draft(str(_draft(tmp_path)), "art-log")
    payload = json.loads((logs_dir / "quality_review_art-log.json").read_text(encoding="utf-8"))
    assert payload["request_id"] == "req-quality"


def test_strict_exit_codes(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria([5] * 8 + [3] * 5), "priority_fixes": [], "improved_body": "body"}))
    rc = quality_review.main(["--draft", str(_draft(tmp_path)), "--article-id", "art-strict", "--strict"])
    assert rc == 1


def test_korean_utf8_safe(tmp_path, monkeypatch):
    path = tmp_path / "draft.md"
    path.write_text("# 제목\n\n한글 본문", encoding="utf-8")
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria([5] * 13), "priority_fixes": [], "improved_body": "개선 본문"}))
    result = quality_review.review_draft(str(path), "art-ko")
    assert "개선" in result["improved_body"]


def test_dry_run_skips_llm(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_review, "get_provider", lambda: NoCallProvider())
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-dry", dry_run=True)
    assert result["request_id"] is None
    assert result["total_tokens"] > 0


def test_local_threshold_overrides_model_claim(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(
        quality_review,
        "get_provider",
        lambda: FakeProvider(
            {
                "verdict": "pass",
                "publishable": True,
                "decision": "publish",
                "criteria_scores": _criteria([5] * 8 + [3] * 5),
                "priority_fixes": [],
                "improved_body": "body",
            }
        ),
    )
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-override")
    assert result["verdict"] == "fail"
    assert result["publishable"] is False
    assert result["decision"] == "rewrite"


def test_quality_review_cap_exceeded_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_review, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(quality_review, "COST_DIR", tmp_path / "costs")
    monkeypatch.setattr(quality_review, "get_provider", lambda: FakeProvider({"criteria_scores": _criteria([5] * 13), "priority_fixes": [], "improved_body": "body"}))
    monkeypatch.setenv("QUALITY_REVIEW_MONTHLY_USD_CAP", "0.0001")
    result = quality_review.review_draft(str(_draft(tmp_path)), "art-cap")
    assert result["verdict"] == "fail"
    assert result["cost_status"]["cap_exceeded"] is True
