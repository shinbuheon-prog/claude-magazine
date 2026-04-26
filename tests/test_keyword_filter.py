"""keyword_filter 휴리스틱 점수 단위 테스트."""
from __future__ import annotations

from pipeline.keyword_filter import _classify_category, score_entry


def test_strong_keyword_claude_high_score():
    score, breakdown, cat = score_entry(
        title="Claude Sonnet 4.6 신규 기능 발표",
        description="Anthropic이 Claude Sonnet 4.6의 새로운 기능을 발표했습니다.",
    )
    assert score >= 0.5
    assert any(k.startswith("strong:claude") for k in breakdown)
    assert any(k.startswith("strong:anthropic") for k in breakdown)


def test_industry_korea_locale():
    score, breakdown, cat = score_entry(
        title="AWS Bedrock에서 Claude 운영 한국 사례",
        description="한국 기업의 AWS Bedrock + Claude 운영 사례를 분석합니다.",
        publisher="Classmethod Korea",
    )
    assert any(k.startswith("industry:bedrock") for k in breakdown)
    assert any(k.startswith("industry:aws") for k in breakdown)
    assert any(k.startswith("locale:") for k in breakdown)
    assert score >= 0.5


def test_negative_keyword_reduces_score():
    score_normal, _, _ = score_entry(
        title="Claude의 새 기능 분석",
        description="Anthropic의 Claude 신규 기능 운영 시사점.",
    )
    score_hyped, breakdown, _ = score_entry(
        title="혁명적 Claude의 새 기능 분석",
        description="Anthropic의 게임 체인저 신규 기능 운영 시사점.",
    )
    assert score_hyped < score_normal
    assert any(k.startswith("negative:") for k in breakdown)


def test_no_keyword_low_score():
    score, _, _ = score_entry(
        title="오늘 날씨가 좋습니다",
        description="공원에 산책 갔습니다.",
    )
    assert score < 0.3


def test_classify_category_feature():
    cat = _classify_category(
        "Claude Code 멀티에이전트 운영체계",
        "Anthropic multi-agent practice",
    )
    assert cat == "feature"


def test_classify_category_deep_dive():
    cat = _classify_category(
        "Bedrock 403 트러블슈팅",
        "AWS Bedrock 운영 중 403 fix",
    )
    assert cat == "deep_dive"


def test_classify_category_review():
    cat = _classify_category(
        "Drawio Skill 사용 후기",
        "Claude Drawio 도구 review",
    )
    assert cat == "review"


def test_classify_category_none_for_irrelevant():
    cat = _classify_category("일반 뉴스", "특이사항 없음")
    assert cat is None


def test_topics_strong_keyword_match():
    score, breakdown, _ = score_entry(
        title="신규 발표",
        description="설명",
        topics=["claude", "anthropic"],
    )
    assert score > 0
    assert any(k.startswith("strong:claude") for k in breakdown)


def test_korean_text_handles_lowercase():
    """한국어 본문에 대해서도 영문 키워드 매칭이 작동하는지 확인."""
    score, breakdown, _ = score_entry(
        title="MCP(Model Context Protocol)란? — Claude Code 입문",
        description="Anthropic의 MCP 프로토콜을 한국어로 정리합니다.",
    )
    # MCP, Model Context Protocol, Claude Code, Anthropic 모두 매칭
    assert score >= 0.5
    assert "strong:mcp" in breakdown
    assert "strong:anthropic" in breakdown
