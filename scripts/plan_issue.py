"""
월간 플랜 관리 CLI (TASK_036)

21꼭지 월간 매거진 제작 진행 상황을 YAML 매니페스트로 관리.

사용법:
    python scripts/plan_issue.py init --month 2026-05 --theme "..."
    python scripts/plan_issue.py add-article --month 2026-05 --slug X --category feature --title "..." --pages 14
    python scripts/plan_issue.py update-status --month 2026-05 --slug X --status draft
    python scripts/plan_issue.py status --month 2026-05 [--json]
    python scripts/plan_issue.py list
    python scripts/plan_issue.py validate --month 2026-05
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32" and not getattr(sys.stdout, "_utf8_wrapped", False):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout._utf8_wrapped = True  # type: ignore[attr-defined]
        except Exception:
            pass

try:
    import yaml  # type: ignore
except ImportError:
    print("❌ PyYAML 미설치 — `pip install PyYAML`", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = ROOT / "drafts" / "issues"
ISSUES_DIR.mkdir(parents=True, exist_ok=True)

VALID_CATEGORIES = {"cover", "feature", "deep_dive", "insight", "interview", "review"}
VALID_STATUSES = [
    "planning", "brief", "draft", "fact_check", "lint", "approved", "published"
]

STATUS_ICONS = {
    "published": "✅",
    "approved": "🟢",
    "lint": "🟡",
    "fact_check": "🟠",
    "draft": "🔵",
    "brief": "⚪",
    "planning": "⬜",
}


# ── 파일 I/O ──────────────────────────────────────

def _issue_path(month: str) -> Path:
    return ISSUES_DIR / f"{month}.yml"


def _load_issue(month: str) -> dict:
    path = _issue_path(month)
    if not path.exists():
        raise FileNotFoundError(f"이슈 플랜 없음: {path} — `plan_issue.py init --month {month}` 로 생성하세요.")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_issue(month: str, data: dict) -> None:
    path = _issue_path(month)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)


# ── 커맨드 핸들러 ─────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    path = _issue_path(args.month)
    if path.exists():
        print(f"⚠️  이미 존재: {path}")
        print("   덮어쓰려면 파일을 수동 삭제 후 다시 실행하세요.")
        return 1

    data = {
        "issue": args.month,
        "theme": args.theme,
        "editor_in_chief": args.editor or "편집장",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "articles": [],
        "sections_order": [
            "feature", "deep_dive", "insight", "interview", "review"
        ],
    }
    _save_issue(args.month, data)
    print(f"✅ 이슈 초기화 완료: {path}")
    print(f"   테마: {args.theme}")
    return 0


def cmd_add_article(args: argparse.Namespace) -> int:
    if args.category not in VALID_CATEGORIES:
        print(f"❌ 카테고리 오류: {args.category} (가능: {sorted(VALID_CATEGORIES)})", file=sys.stderr)
        return 1

    data = _load_issue(args.month)
    articles = data.setdefault("articles", [])

    # 중복 slug 체크
    if any(a["slug"] == args.slug for a in articles):
        print(f"❌ 중복 slug: {args.slug}", file=sys.stderr)
        return 1

    article = {
        "slug": args.slug,
        "category": args.category,
        "title_draft": args.title,
        "assignee": args.assignee or "",
        "source_ids": args.source_ids or [],
        "target_pages": args.pages,
        "status": "planning",
        "brief_path": "",
        "draft_path": "",
        "ghost_post_id": "",
    }
    articles.append(article)
    _save_issue(args.month, data)
    print(f"✅ 꼭지 추가: {args.slug} ({args.category}, {args.pages}p)")
    return 0


def cmd_update_status(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUSES:
        print(f"❌ 상태 오류: {args.status}", file=sys.stderr)
        print(f"   가능: {VALID_STATUSES}", file=sys.stderr)
        return 1

    data = _load_issue(args.month)
    articles = data.get("articles", [])
    found = None
    for a in articles:
        if a["slug"] == args.slug:
            found = a
            break

    if not found:
        print(f"❌ slug 없음: {args.slug}", file=sys.stderr)
        return 1

    prev = found["status"]
    found["status"] = args.status

    # 순방향 스킵 경고 (차단은 안 함)
    prev_idx = VALID_STATUSES.index(prev) if prev in VALID_STATUSES else 0
    new_idx = VALID_STATUSES.index(args.status)
    if new_idx > prev_idx + 1:
        print(f"⚠️  상태 점프: {prev} → {args.status} (중간 단계 스킵)")

    if args.path:
        # path 필드 자동 매핑 (brief·draft·ghost_post_id)
        if args.status == "brief":
            found["brief_path"] = args.path
        elif args.status == "draft":
            found["draft_path"] = args.path
        elif args.status == "published":
            found["ghost_post_id"] = args.path

    _save_issue(args.month, data)
    print(f"✅ {args.slug}: {prev} → {args.status}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data = _load_issue(args.month)

    # 상태별 카운트
    counts = {s: 0 for s in VALID_STATUSES}
    for a in data.get("articles", []):
        s = a.get("status", "planning")
        counts[s] = counts.get(s, 0) + 1

    total = sum(counts.values())
    published = counts["published"]

    if args.json:
        out = {
            "month": data.get("issue"),
            "theme": data.get("theme"),
            "counts": counts,
            "total": total,
            "published": published,
            "progress_pct": round(published / total * 100, 1) if total else 0,
            "articles": data.get("articles", []),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"=== {data.get('issue')} \"{data.get('theme', '')}\" ===")
    print(f"편집장: {data.get('editor_in_chief', '')}")
    print(f"생성일: {data.get('created_at', '')[:10]}")
    print()
    print(f"꼭지 {total}개:")
    for status in reversed(VALID_STATUSES):
        count = counts.get(status, 0)
        if count > 0:
            icon = STATUS_ICONS.get(status, "·")
            label = {
                "published": "발행 완료",
                "approved": "승인 대기",
                "lint": "lint 진행",
                "fact_check": "팩트체크",
                "draft": "초안 작성",
                "brief": "브리프",
                "planning": "기획",
            }.get(status, status)
            print(f"  {icon} {label:<10} {count:>3}  ({status})")

    progress = (published / total * 100) if total else 0
    print(f"\n진행률: {progress:.1f}% ({published}/{total} published)")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    issues = sorted(ISSUES_DIR.glob("*.yml"))
    if not issues:
        print("(등록된 이슈 없음)")
        return 0

    print(f"=== 이슈 목록 ({len(issues)}개) ===")
    for path in issues:
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            month = data.get("issue", path.stem)
            theme = data.get("theme", "")
            article_count = len(data.get("articles", []))
            published_count = sum(
                1 for a in data.get("articles", []) if a.get("status") == "published"
            )
            print(f"  {month}  ({published_count}/{article_count} published)  {theme}")
        except Exception as exc:
            print(f"  {path.stem}  [❌ 로드 실패: {exc}]")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    data = _load_issue(args.month)
    errors: list[str] = []
    warnings: list[str] = []

    if not data.get("issue"):
        errors.append("issue 필드 누락")
    if not data.get("theme"):
        errors.append("theme 필드 누락")

    articles = data.get("articles", [])
    if len(articles) == 0:
        warnings.append("articles 0개 — 아직 꼭지 추가되지 않음")

    slugs_seen = set()
    total_pages = 0
    cat_counts: dict[str, int] = {}

    for a in articles:
        slug = a.get("slug", "?")
        if slug in slugs_seen:
            errors.append(f"중복 slug: {slug}")
        slugs_seen.add(slug)

        cat = a.get("category")
        if cat not in VALID_CATEGORIES:
            errors.append(f"{slug}: 잘못된 category={cat}")
        else:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        status = a.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{slug}: 잘못된 status={status}")

        pages = a.get("target_pages", 0)
        if not isinstance(pages, int) or pages < 1:
            warnings.append(f"{slug}: target_pages 부적절 ({pages})")
        else:
            total_pages += pages

    print(f"=== {args.month} 플랜 검증 ===")
    print(f"꼭지: {len(articles)}개")
    print(f"카테고리 분포: {cat_counts}")
    print(f"누적 페이지: {total_pages}p")
    print()

    if errors:
        print("❌ 오류:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("⚠️  경고:")
        for w in warnings:
            print(f"  - {w}")
    if not errors and not warnings:
        print("✅ 유효함")

    return 1 if errors else 0


# ── main ──────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="월간 이슈 플랜 관리")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="새 호 초기화")
    p_init.add_argument("--month", required=True, help="YYYY-MM")
    p_init.add_argument("--theme", required=True, help="이달의 주제")
    p_init.add_argument("--editor", help="편집장 이름 (선택)")

    p_add = sub.add_parser("add-article", help="꼭지 추가")
    p_add.add_argument("--month", required=True)
    p_add.add_argument("--slug", required=True)
    p_add.add_argument("--category", required=True, help=f"{sorted(VALID_CATEGORIES)}")
    p_add.add_argument("--title", required=True, help="제목 초안")
    p_add.add_argument("--pages", type=int, required=True, help="목표 페이지 수")
    p_add.add_argument("--assignee", help="담당 편집자")
    p_add.add_argument("--source-ids", nargs="*", default=[])

    p_upd = sub.add_parser("update-status", help="꼭지 상태 변경")
    p_upd.add_argument("--month", required=True)
    p_upd.add_argument("--slug", required=True)
    p_upd.add_argument("--status", required=True, help=f"{VALID_STATUSES}")
    p_upd.add_argument("--path", help="brief/draft/ghost_post_id 경로 자동 매핑")

    p_st = sub.add_parser("status", help="진행 현황")
    p_st.add_argument("--month", required=True)
    p_st.add_argument("--json", action="store_true")

    p_ls = sub.add_parser("list", help="이슈 목록")

    p_val = sub.add_parser("validate", help="플랜 유효성 검증")
    p_val.add_argument("--month", required=True)

    args = parser.parse_args()

    handlers = {
        "init": cmd_init,
        "add-article": cmd_add_article,
        "update-status": cmd_update_status,
        "status": cmd_status,
        "list": cmd_list,
        "validate": cmd_validate,
    }

    try:
        return handlers[args.cmd](args)
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
