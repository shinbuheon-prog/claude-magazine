"""
classmethodkr 기술블로그 월별 베스트 기고 큐레이터.

매거진 "Korea Spotlight" 코너의 데이터 소스. 월 단위 RSS에서
Claude/AI 관련 베스트 N건을 휴리스틱 점수로 선정 → 마크다운 보고서 출력.

자체 콘텐츠(rights_status: free)이므로 풀 요약 + 외부 링크 자유.
매거진 본문에서 블로그로 트래픽 유입을 유도하는 코너.

사용:
    python scripts/curate_classmethodkr_best.py --month 2026-04
    python scripts/curate_classmethodkr_best.py --month 2026-04 --top 5
    python scripts/curate_classmethodkr_best.py --month 2026-04 --topic claude
    python scripts/curate_classmethodkr_best.py --month 2026-04 --dry-run

산출물: reports/classmethodkr_best_YYYY-MM.md
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
RSS_URL = "https://rss.blog.naver.com/classmethodkr.xml"
NETWORK_TIMEOUT = 15
USER_AGENT = "claude-magazine/0.3 (Korea Spotlight curator)"

# 본인(편집장) 추정 식별자 — 자가 홍보 명시 표기에 사용
EDITOR_AUTHOR_MARKERS = ["Shin부장", "Shin 부장", "shin.buheon", "신부헌"]

# 매거진 정체성과 정합도 — topic 점수
TOPIC_WEIGHTS = {
    "claude": 5,
    "anthropic": 5,
    "openclaw": 4,
    "cowork": 4,
    "claude code": 4,
    "claude.md": 3,
    "mcp": 4,
    "ai": 2,
    "aws": 1,
}


def fetch_rss(url: str = RSS_URL) -> list[dict]:
    """RSS XML 파싱 → item dict list."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    ch = root.find("channel")
    if ch is None:
        return []
    items = []
    for it in ch.findall("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        desc_raw = it.findtext("description") or ""
        desc = re.sub(r"<[^>]+>", "", desc_raw).strip()
        cats = [c.text for c in it.findall("category") if c.text]
        items.append({
            "title": title,
            "link": link,
            "pub_date_raw": pub,
            "description": desc,
            "categories": cats,
        })
    return items


def parse_pub_date(pub_raw: str) -> datetime | None:
    if not pub_raw:
        return None
    try:
        return parsedate_to_datetime(pub_raw)
    except (TypeError, ValueError):
        return None


def filter_by_month(items: list[dict], month: str) -> list[dict]:
    """month=YYYY-MM 형식. 해당 월에 발행된 item만 반환."""
    out = []
    for it in items:
        d = parse_pub_date(it["pub_date_raw"])
        if d is None:
            continue
        if d.strftime("%Y-%m") == month:
            it["pub_date"] = d
            out.append(it)
    return out


def score_item(item: dict, topic_filter: str | None = None) -> tuple[int, dict]:
    """휴리스틱 점수 계산. (score, breakdown)."""
    title_lower = item["title"].lower()
    desc_lower = item["description"].lower()
    text = f"{title_lower} {desc_lower}"
    breakdown: dict[str, int] = {}

    # topic 가중치
    for kw, w in TOPIC_WEIGHTS.items():
        if kw in text:
            breakdown[f"topic:{kw}"] = w

    # 카테고리 매칭
    for cat in item.get("categories", []):
        cat_l = cat.lower()
        if "claude" in cat_l or "ai" in cat_l:
            breakdown["category:claude_or_ai"] = 3

    # 본인(편집장) 작성글 — 자가 홍보 보너스 (단, 명시 표기 의무)
    is_editor = any(m.lower() in desc_lower for m in EDITOR_AUTHOR_MARKERS)
    if is_editor:
        breakdown["author:editor"] = 2
        item["is_editor_post"] = True
    else:
        item["is_editor_post"] = False

    # 길이 보너스 (description이 길수록 본문 충실)
    if len(item["description"]) > 100:
        breakdown["depth:long_desc"] = 1

    # topic_filter 강제: 미포함 시 0점
    if topic_filter:
        tf = topic_filter.lower()
        if tf not in text:
            return 0, {"filtered_out": f"missing topic={tf}"}

    return sum(breakdown.values()), breakdown


def detect_author(desc: str) -> str:
    """description 첫 줄에서 작성자 추출 ('안녕하세요 ... 입니다.')."""
    m = re.search(r"안녕하세요[,\s]*\s*클래스메소드코리아\s+([A-Za-z가-힣\s]+?)(?:입니다|이에요|예요)", desc[:200])
    if m:
        return m.group(1).strip()
    m2 = re.search(r"안녕하세요[,\s]*\s*([A-Za-z가-힣]+(?:부장|매니저|님)?)\s*입니다", desc[:200])
    if m2:
        return m2.group(1).strip()
    return "(작성자 미상)"


def render_report(month: str, top_items: list[tuple[int, dict, dict]], total_in_month: int) -> str:
    """매거진 Korea Spotlight 코너용 마크다운 생성."""
    out = []
    out.append(f"# Korea Spotlight — Classmethod Korea {month} 베스트 기고 TOP {len(top_items)}")
    out.append("")
    out.append("**대상 블로그**: [Classmethod Korea Tech Blog](https://blog.naver.com/classmethodkr)")
    out.append(f"**대상 기간**: {month} (1일~월말)")
    out.append(f"**전체 기고 건수**: {total_in_month}건")
    out.append("**선정 기준**: 매거진 정체성 정합도(claude·anthropic·openclaw·cowork·mcp 가중치) + 카테고리 + 본문 충실도. 본인(편집장) 기고는 자가 홍보 보너스(+2) 부여하되 본 코너에서 명시 표기.")
    out.append("**라이선스**: 자체 콘텐츠 (rights_status: free) — 풀 요약 + 외부 링크 자유")
    out.append(f"**큐레이션 시각**: {datetime.now(timezone.utc).isoformat()}")
    out.append("")
    out.append("---")
    out.append("")

    out.append("## editor_approval (Korea Spotlight Gate)")
    out.append("")
    out.append("```yaml")
    out.append("status: pending           # pending | approved | rejected | partial")
    out.append("reviewer: <편집자 서명>")
    out.append("reviewed_at: <YYYY-MM-DDTHH:MM+09:00>")
    out.append("notes: |")
    out.append("  - TOP N건 채택 여부 / 자가 홍보 표기 유지 / 매거진 코너 페이지 수 확정")
    out.append("```")
    out.append("")
    out.append("---")
    out.append("")

    out.append("## 선정 기고 상세")
    out.append("")

    for rank, (score, item, breakdown) in enumerate(top_items, 1):
        author = detect_author(item["description"])
        editor_badge = "  ⭐ **편집장 기고** — 자가 홍보 표기" if item.get("is_editor_post") else ""
        out.append(f"### #{rank}. {item['title']}{editor_badge}")
        out.append("")
        out.append(f"- **작성자**: {author}")
        out.append(f"- **발행일**: {item['pub_date'].strftime('%Y-%m-%d (%a)')}")
        out.append(f"- **카테고리**: {', '.join(item.get('categories', []))}")
        out.append(f"- **블로그 링크**: <{item['link'].split('?')[0]}>")
        out.append(f"- **점수**: {score} (breakdown: {breakdown})")
        out.append("")
        out.append("**1줄 요약 (편집자 작성 대기)**:")
        out.append("> _<편집자가 본문 읽고 1줄 요약 작성>_")
        out.append("")
        out.append("**원문 인트로 (RSS description)**:")
        # description 첫 200자 + 출처 표시
        intro = item["description"][:200] + ("..." if len(item["description"]) > 200 else "")
        out.append(f"> {intro}")
        out.append("")
        out.append("**매거진 활용 각도 (편집자 기입)**:")
        out.append("- _<예: 5월 호 Korea Spotlight 코너에 풀 인용 + 블로그 링크 박스>_")
        out.append("- _<예: 5월 호 본문 기사의 사이드바로 결합 (관련 클러스터: ...)>_")
        out.append("")
        out.append("---")
        out.append("")

    out.append("## 매거진 코너 채택 후 다음 단계")
    out.append("")
    out.append("1. 편집자가 위 `editor_approval` YAML을 `approved`로 갱신")
    out.append("2. 채택된 게시글의 source_id가 source_registry에 등록되었는지 확인 (자동 — `python pipeline/source_ingester.py --feed 'Classmethod Korea Tech Blog' --since-days 30`)")
    out.append("3. 매거진 plan_issue.py에 'Korea Spotlight' 꼭지 추가:")
    out.append("   ```bash")
    out.append("   python scripts/plan_issue.py add-article --month 2026-05 \\")
    out.append("       --slug korea-spotlight --category review --pages 3 \\")
    out.append("       --title 'Korea Spotlight — 사내 베스트 기고 TOP 3'")
    out.append("   ```")
    out.append("4. draft_writer가 본 보고서를 입력으로 삼아 매거진 본문 생성 (편집자 1줄 요약 + 활용 각도 채워진 상태에서)")
    out.append("5. 본문 하단에 '블로그에서 더 보기 →' 링크 박스 자동 삽입 (트래픽 유입 트래커 UTM 파라미터 옵션)")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## AI 사용 고지")
    out.append("")
    out.append("본 큐레이션 보고서는 RSS 메타데이터(제목·발행일·카테고리·인트로 200자)를 기반으로 휴리스틱 점수 알고리즘으로 작성됐습니다. LLM 호출 0회, 본문은 열람·복사하지 않았습니다(외부 링크 참조만). 편집자 1줄 요약·활용 각도 작성은 매거진 발행 단계에서 수동 또는 Sonnet 보조로 진행됩니다.")
    out.append("")
    out.append("## 변경 이력")
    out.append("")
    out.append(f"- {datetime.now().strftime('%Y-%m-%d')}: 초안 자동 생성 (curate_classmethodkr_best.py).")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classmethod Korea 월별 베스트 기고 큐레이터")
    parser.add_argument("--month", required=True, help="대상 월 (YYYY-MM)")
    parser.add_argument("--top", type=int, default=3, help="선정 건수 (default 3)")
    parser.add_argument("--topic", help="강제 토픽 필터 (예: claude). 미포함 게시글 제외")
    parser.add_argument("--dry-run", action="store_true", help="파일 저장 없이 stdout 출력만")
    parser.add_argument("--out", help="출력 파일 경로 (기본: reports/classmethodkr_best_YYYY-MM.md)")
    args = parser.parse_args(argv)

    # 월 형식 검증
    try:
        datetime.strptime(args.month, "%Y-%m")
    except ValueError:
        print(f"❌ --month 형식 오류: {args.month} (YYYY-MM 필요)", file=sys.stderr)
        return 1

    print(f"[1/4] RSS fetch: {RSS_URL}")
    items = fetch_rss()
    print(f"      → {len(items)} items in feed")

    print(f"[2/4] {args.month} 월 필터링")
    in_month = filter_by_month(items, args.month)
    print(f"      → {len(in_month)} items in {args.month}")
    if not in_month:
        print(f"❌ {args.month}에 발행된 기고가 없습니다.", file=sys.stderr)
        return 1

    print(f"[3/4] 점수 계산 (topic_filter={args.topic})")
    scored = []
    for it in in_month:
        score, breakdown = score_item(it, topic_filter=args.topic)
        if score > 0:
            scored.append((score, it, breakdown))
    scored.sort(key=lambda x: x[0], reverse=True)
    print(f"      → {len(scored)} items scored > 0")

    if not scored:
        print(f"❌ 점수 > 0인 기고가 없습니다 (topic={args.topic}).", file=sys.stderr)
        return 1

    top = scored[: args.top]
    print(f"      → TOP {len(top)} 선정 (점수: {[t[0] for t in top]})")

    print("[4/4] 보고서 렌더")
    report = render_report(args.month, top, len(in_month))

    if args.dry_run:
        print()
        print("=== DRY RUN — stdout output ===")
        print(report[:2000])
        print("...(truncated)")
        return 0

    out_path = Path(args.out) if args.out else (REPORTS_DIR / f"classmethodkr_best_{args.month}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"      ✓ 저장: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
