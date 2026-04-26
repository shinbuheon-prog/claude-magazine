"""
Claude 키워드 필터 + 적합도 점수 (외부 큐레이션 파이프라인 L2 계층).

source_registry에 등록된 후보 source 또는 raw RSS entry에 대해
prompts/template_article_selector.txt 기준의 휴리스틱 점수를 계산.

LLM 호출 없이 동작 (휴리스틱만) — 비용 0, 속도 빠름.
LLM 격상은 prompts/template_article_selector.txt를 직접 brief_generator에 전달해 수행.

외부 큐레이션 파이프라인 5계층 중 L2 계층:
  L1 수집 → **L2 키워드 필터(본 모듈)** → L3 요약 → L4 클러스터링 → L5 Gate 1 채택

사용:
    from pipeline.keyword_filter import score_entry, batch_filter_registered

    # 단일 entry
    score, breakdown, magazine_category = score_entry(title="...", description="...", topics=[...])

    # source_registry 등록된 후보 일괄 필터
    results = batch_filter_registered(article_id_filter=None, threshold=0.6)

CLI:
    python pipeline/keyword_filter.py --threshold 0.6 --top 20
    python pipeline/keyword_filter.py --article-id monthly_digest_2026-04-W3
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "source_registry.db"

# 강 키워드 (1+ 매칭 → 자동 채택 후보)
STRONG_KEYWORDS = {
    "claude": 5,
    "anthropic": 5,
    "constitutional ai": 4,
    "mcp": 4,
    "model context protocol": 4,
    "agent skill": 4,
    "sonnet 4": 4,
    "opus 4": 4,
    "haiku 4": 4,
    "claude code": 4,
    "claude cowork": 4,
    "openclaw": 4,
}

# 약 키워드 (2+ 동시 매칭 → 채택)
WEAK_KEYWORDS = {
    "llm": 1,
    "agent": 1,
    "tool use": 1,
    "rag": 1,
    "prompt": 1,
    "context": 1,
    "subagent": 1,
    "extended thinking": 2,
    "computer use": 2,
}

# 메타 키워드 (3+ 동시 매칭 + 강·약 1+ → 채택)
META_KEYWORDS = {
    "evaluation": 1,
    "benchmark": 1,
    "alignment": 1,
    "safety": 1,
    "policy": 1,
    "governance": 1,
}

# 산업 구조 변화 가중치 (사용자 프롬프트 2 기준 1·2·3)
INDUSTRY_KEYWORDS = {
    "openai": 2,
    "google": 2,
    "microsoft": 2,
    "aws": 2,
    "bedrock": 3,
    "nvidia": 2,
    "meta": 2,
    "huggingface": 2,
    "deepmind": 2,
    "gemini": 1,
    "gpt": 1,
    "copilot": 1,
}

# 한국·일본 시장 시사점 가중치 (사용자 프롬프트 2 기준 4)
LOCALE_KEYWORDS = {
    "korea": 1,
    "korean": 1,
    "한국": 1,
    "japan": 1,
    "japanese": 1,
    "일본": 1,
    "classmethod": 2,
    "kotra": 1,
    "naver": 1,
    "kakao": 1,
    "samsung": 1,
}

# 매거진 카테고리 매핑 가중치 (강 키워드 + 패턴, dict 정의 순으로 우선 평가)
# "feature"가 가장 먼저 평가되도록 상단에 배치 — multi-agent / 멀티에이전트 / 운영체계 매칭 시 feature 채택
CATEGORY_HINTS = {
    "feature": ["multi-agent", "multi agent", "멀티에이전트", "운영체계", "엔터프라이즈"],
    "interview": ["interview", "인터뷰", "대담"],
    "insight": ["benchmark", "evaluation", "통계", "ranking", "release timeline"],
    "review": ["skill", "도구", "tool", "vs ", "compare"],
    "deep_dive": ["403", "trouble", "fix", "운영", "operation", "endpoint"],
}

# 부정 가중치 (사용자 프롬프트 2 기준 — 단순 홍보·과장)
NEGATIVE_PATTERNS = [
    "revolutionary",
    "game changer",
    "혁명적",
    "게임 체인저",
    "막대한",
    "전세계 1위",
]


def _classify_category(title: str, description: str) -> str | None:
    """제목·설명에서 매거진 카테고리 후보 추정. 매칭 없으면 None."""
    text = f"{title} {description}".lower()
    for category, hints in CATEGORY_HINTS.items():
        for hint in hints:
            if hint in text:
                return category
    return None


def score_entry(
    title: str,
    description: str = "",
    topics: list[str] | None = None,
    publisher: str = "",
) -> tuple[float, dict, str | None]:
    """단일 entry 점수 계산.

    Returns:
        (relevance_score: float 0~1, breakdown: dict, magazine_category: str | None)
    """
    text = f"{title} {description} {publisher}".lower()
    topics_set = {t.lower() for t in (topics or [])}
    breakdown: dict[str, int] = {}

    # 강 키워드
    strong_hits = 0
    for kw, w in STRONG_KEYWORDS.items():
        if kw in text or kw.replace(" ", "_") in topics_set:
            breakdown[f"strong:{kw}"] = w
            strong_hits += 1

    # 약 키워드 (2+ 매칭 시 누적)
    weak_hits = 0
    weak_score = 0
    for kw, w in WEAK_KEYWORDS.items():
        if kw in text:
            weak_hits += 1
            weak_score += w
    if weak_hits >= 2:
        breakdown["weak_combined"] = weak_score

    # 메타 키워드 (3+ + 강·약 1+ 시 누적)
    meta_hits = 0
    meta_score = 0
    for kw, w in META_KEYWORDS.items():
        if kw in text:
            meta_hits += 1
            meta_score += w
    if meta_hits >= 3 and (strong_hits > 0 or weak_hits > 0):
        breakdown["meta_combined"] = meta_score

    # 산업 구조 키워드 (사용자 프롬프트 2 기준 1·3)
    for kw, w in INDUSTRY_KEYWORDS.items():
        if kw in text:
            breakdown[f"industry:{kw}"] = w

    # 한국·일본 시장 (사용자 프롬프트 2 기준 4)
    for kw, w in LOCALE_KEYWORDS.items():
        if kw in text:
            breakdown[f"locale:{kw}"] = w

    # 부정 가중치 (과장·홍보)
    negative_score = 0
    for pat in NEGATIVE_PATTERNS:
        if pat in text:
            negative_score -= 3
            breakdown[f"negative:{pat}"] = -3

    # 합산 → 0~1 정규화
    raw_score = sum(v for v in breakdown.values())
    # 강 키워드 1개 (5점) + 산업 1개 (2점) + 한국 1개 (1점) = 8점이 평균적인 "확실 채택"
    # 0~10 범위를 0~1로 매핑
    normalized = max(0.0, min(1.0, raw_score / 10.0))

    # 매거진 카테고리 추정
    magazine_category = _classify_category(title, description)

    return normalized, breakdown, magazine_category


def batch_filter_registered(
    article_id_filter: str | None = None,
    threshold: float = 0.6,
) -> list[dict]:
    """source_registry 등록된 후보를 일괄 필터.

    Args:
        article_id_filter: 특정 article_id 만 필터 (예: 'monthly_digest_2026-04-W3')
        threshold: relevance_score 컷 (기본 0.6 — auto-accept threshold)

    Returns:
        list of dict: source_id, url, score, breakdown, magazine_category, decision
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"source_registry DB 없음: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        if article_id_filter:
            rows = conn.execute(
                "SELECT * FROM sources WHERE article_id = ? ORDER BY retrieved_at ASC",
                (article_id_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sources ORDER BY retrieved_at DESC LIMIT 500"
            ).fetchall()

        results = []
        for row in rows:
            source_id = row["source_id"]
            url = row["url"]
            publisher = row["publisher"] or ""
            # source_id에서 슬러그 추출 (예: sns-blog-20260421-claude-code-multi-agent-practice)
            title = source_id  # 실제 title 필드는 source_registry에 없음 — slug 사용
            score, breakdown, mag_cat = score_entry(
                title=title,
                description="",
                publisher=publisher,
            )
            decision = (
                "auto_accept"
                if score >= threshold
                else "review_pending"
                if score >= 0.3
                else "skip"
            )
            results.append({
                "source_id": source_id,
                "url": url,
                "publisher": publisher,
                "score": round(score, 3),
                "breakdown": breakdown,
                "magazine_category": mag_cat,
                "decision": decision,
            })

        # 점수 내림차순 정렬
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Claude 키워드 필터 — 외부 큐레이션 파이프라인 L2 계층",
    )
    parser.add_argument("--article-id", help="특정 article_id 만 필터")
    parser.add_argument("--threshold", type=float, default=0.6, help="auto-accept 점수 (기본 0.6)")
    parser.add_argument("--top", type=int, default=20, help="상위 N건 출력 (기본 20)")
    parser.add_argument("--json", action="store_true", help="JSON 형식 출력")
    args = parser.parse_args(argv)

    try:
        results = batch_filter_registered(
            article_id_filter=args.article_id,
            threshold=args.threshold,
        )
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    top = results[: args.top]

    if args.json:
        print(json.dumps(top, indent=2, ensure_ascii=False))
        return 0

    print("=== Claude 키워드 필터 결과 ===")
    print(f"전체 {len(results)}건 / TOP {len(top)}건 표시 (threshold {args.threshold})")
    print()
    accept = sum(1 for r in results if r["decision"] == "auto_accept")
    review = sum(1 for r in results if r["decision"] == "review_pending")
    skip = sum(1 for r in results if r["decision"] == "skip")
    print(f"  auto_accept: {accept}건 (≥{args.threshold})")
    print(f"  review_pending: {review}건 (0.3 ≤ score < {args.threshold})")
    print(f"  skip: {skip}건 (<0.3)")
    print()

    for i, r in enumerate(top, 1):
        marker = "✅" if r["decision"] == "auto_accept" else ("🟡" if r["decision"] == "review_pending" else "❌")
        cat = f" [{r['magazine_category']}]" if r["magazine_category"] else ""
        print(f"{marker} #{i} {r['source_id'][:60]}{cat}")
        print(f"    score={r['score']} / decision={r['decision']}")
        bd_summary = ", ".join(f"{k}={v}" for k, v in list(r["breakdown"].items())[:5])
        if bd_summary:
            print(f"    breakdown: {bd_summary}{'...' if len(r['breakdown']) > 5 else ''}")
        print()

    return 0


if __name__ == "__main__":
    # 스모크 테스트 (CLI 진입점이 아닐 때)
    if len(sys.argv) == 1:
        print("=== keyword_filter 스모크 테스트 ===")
        score, breakdown, cat = score_entry(
            title="Claude Code 멀티에이전트 운영 가이드 — Sonnet 4.6과 MCP 활용",
            description="Anthropic의 Claude Code에서 멀티에이전트 패턴을 한국 사례로 분석",
            topics=["claude", "multi-agent"],
        )
        print(f"점수: {score} / 카테고리: {cat}")
        print(f"breakdown: {breakdown}")
        assert score >= 0.6, f"기대: ≥0.6, 실제: {score}"
        assert cat == "feature", f"기대: feature, 실제: {cat}"
        print("✓ 스모크 테스트 통과")
        sys.exit(0)
    sys.exit(main())
