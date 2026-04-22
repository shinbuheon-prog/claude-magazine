"""
weekly_improvement.py — TASK_027 자율 개선 루프 진입점

매주 일요일 23:00 KST에 Cron 실행되어:
  1) failure_collector.collect_failures(since_days) 호출
  2) sop_updater.analyze_and_propose(failures) 호출 (--dry-run이면 skip)
  3) reports/improvement_YYYY-MM-DD.md 저장 (토요일 기준 날짜)
  4) (옵션) GitHub Issue 자동 생성 --create-issue

사용법:
    python scripts/weekly_improvement.py
    python scripts/weekly_improvement.py --since-days 14
    python scripts/weekly_improvement.py --dry-run
    python scripts/weekly_improvement.py --output reports/custom.md
    python scripts/weekly_improvement.py --create-issue
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

if sys.platform == "win32" and not getattr(sys.stdout, "_cm_utf8", False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        sys.stderr._cm_utf8 = True  # type: ignore[attr-defined]
    except (ValueError, AttributeError):
        pass

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.failure_collector import collect_failures  # noqa: E402
from pipeline.sop_updater import analyze_and_propose  # noqa: E402

REPORTS_DIR = ROOT / "reports"
LOGS_DIR = ROOT / "logs"
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# 보고서 파일명 (토요일 기준)
# ---------------------------------------------------------------------------


def _saturday_of(now: datetime | None = None) -> datetime:
    """주어진 시각(기본 KST 현재) 이전의 가장 가까운 토요일."""
    base = now or datetime.now(timezone.utc)
    # 토요일 = weekday 5 (월=0 .. 일=6)
    delta = (base.weekday() - 5) % 7
    return (base - timedelta(days=delta)).replace(hour=0, minute=0, second=0, microsecond=0)


def default_report_path() -> Path:
    sat = _saturday_of()
    return REPORTS_DIR / f"improvement_{sat.strftime('%Y-%m-%d')}.md"


# ---------------------------------------------------------------------------
# 보고서 렌더링 (마크다운)
# ---------------------------------------------------------------------------


def _render_summary(failures: dict[str, Any]) -> list[str]:
    lint = failures.get("editorial_lint_failures", [])
    corrections = failures.get("editor_corrections", [])
    anomalies = failures.get("langfuse_anomalies", [])
    standards = failures.get("standards_failures", [])

    lint_total = sum(item.get("count", 0) for item in lint)
    corr_total = sum(item.get("count", 0) for item in corrections)
    standards_total = sum(item.get("count", 0) for item in standards)

    def _top3(items: list[dict[str, Any]], key: str) -> str:
        if not items:
            return "없음"
        parts = [f"{item[key]} {item.get('count', 0)}건" for item in items[:3]]
        return ", ".join(parts)

    lines = ["## 요약", ""]
    lines.append(f"- 수집 기간: {failures.get('period', {}).get('from', '')} ~ "
                 f"{failures.get('period', {}).get('to', '')} "
                 f"({failures.get('period', {}).get('days', 0)}일)")
    lines.append(f"- 발행 기사: {failures.get('total_articles', 0)}건")
    lines.append(
        f"- editorial_lint 실패: {lint_total}건 (주요: {_top3(lint, 'check_id')})"
    )
    lines.append(
        f"- standards_checker 실패: {standards_total}건 (주요: {_top3(standards, 'rule_id')})"
    )
    lines.append(
        f"- 편집자 판정: {corr_total}건 (주요: {_top3(corrections, 'type')})"
    )
    if anomalies:
        anomaly_desc = "; ".join(
            f"{a.get('metric')}: {a.get('baseline')} -> {a.get('current')} ({a.get('delta_pct')}%)"
            for a in anomalies
        )
        lines.append(f"- 비정상 메트릭: {anomaly_desc}")
    else:
        lines.append("- 비정상 메트릭: 없음")
    lines.append("")
    return lines


def _render_patterns(proposal: dict[str, Any]) -> list[str]:
    patterns = proposal.get("patterns", [])
    lines = [f"## 반복 패턴 {len(patterns)}건 발견", ""]
    if not patterns:
        lines.append("_충분한 반복 패턴이 탐지되지 않았습니다._")
        lines.append("")
        return lines
    for idx, pattern in enumerate(patterns, start=1):
        name = pattern.get("pattern", "(no name)")
        freq = pattern.get("frequency", 0)
        categories = pattern.get("affected_categories") or []
        evidence = pattern.get("evidence", "")
        cats = ", ".join(categories) if categories else "n/a"
        lines.append(f"### {idx}. {name} (빈도 {freq}, 영향 카테고리: {cats})")
        if evidence:
            lines.append(f"- 근거: {evidence}")
        lines.append("")
    return lines


def _render_updates(proposal: dict[str, Any]) -> list[str]:
    updates = proposal.get("proposed_updates", [])
    updates_sorted = sorted(
        updates, key=lambda u: PRIORITY_ORDER.get(str(u.get("priority") or "medium"), 1)
    )
    lines = [f"## 제안된 업데이트 {len(updates_sorted)}건", ""]
    if not updates_sorted:
        lines.append("_이번 주 제안된 변경 사항은 없습니다._")
        lines.append("")
        return lines

    for update in updates_sorted:
        target = update.get("target_file", "(unspecified)")
        priority = str(update.get("priority") or "medium").upper()
        rationale = update.get("rationale", "")
        impact = update.get("expected_impact", "")
        diff = update.get("diff", "")
        lines.append(f"### [{priority}] {target}")
        if impact:
            lines.append(f"기대 효과: {impact}")
        if rationale:
            lines.append(f"근거: {rationale}")
        lines.append("")
        if diff:
            lines.append("```diff")
            lines.append(diff.rstrip("\n"))
            lines.append("```")
        else:
            lines.append("_diff 미제공 — 사람이 수동으로 초안 작성 필요._")
        lines.append("")
    return lines


def _render_checklist(proposal: dict[str, Any]) -> list[str]:
    updates = proposal.get("proposed_updates", [])
    lines = ["## 사람 승인 필요 체크리스트", ""]
    if not updates:
        lines.append("- [ ] 이번 주 수정 제안 없음 — 실패 수집 로그만 확인")
        lines.append("")
        return lines
    lines.append("아래 절차로 제안을 검토/적용하십시오:")
    lines.append("")
    lines.append("1. `git checkout -b improvement/$(date +%Y-%m-%d)`")
    lines.append("2. 제안된 diff를 수동 적용 (또는 `git apply <diff-file>`)")
    lines.append("3. 로컬에서 관련 스모크 테스트 재실행")
    lines.append("4. `git commit -m \"chore: weekly SOP update\"` + PR 생성")
    lines.append("")
    lines.append("제안별 승인 체크:")
    for update in updates:
        target = update.get("target_file", "(unspecified)")
        priority = str(update.get("priority") or "medium").upper()
        lines.append(f"- [ ] [{priority}] `{target}` 리뷰/적용")
    lines.append("")
    return lines


def render_report(
    failures: dict[str, Any],
    proposal: dict[str, Any],
    period_label: str,
) -> str:
    lines: list[str] = [f"# 주간 개선 제안 — {period_label}", ""]
    lines.extend(_render_summary(failures))
    lines.extend(_render_patterns(proposal))
    lines.extend(_render_updates(proposal))
    lines.extend(_render_checklist(proposal))

    confidence = proposal.get("confidence")
    request_id = proposal.get("opus_request_id")
    lines.append("## 메타")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now(timezone.utc).isoformat()}")
    lines.append(
        f"- Opus request_id: `{request_id}`" if request_id else "- Opus request_id: _n/a (dry-run 또는 호출 실패)_"
    )
    if confidence is not None:
        lines.append(f"- confidence: {confidence}")
    if proposal.get("notes"):
        lines.append(f"- notes: {proposal['notes']}")
    lines.append("")
    lines.append(
        "_본 보고서는 Opus 제안일 뿐이며, 실제 파일 수정은 편집자의 수동 승인 후에만 적용됩니다._"
    )
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 부가 기능: GitHub Issue 생성 / Slack 알림
# ---------------------------------------------------------------------------


def create_github_issue(report_path: Path, proposal: dict[str, Any]) -> str | None:
    """gh CLI가 있으면 issue를 생성하고 URL을 반환."""
    try:
        subprocess.run(["gh", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[warn] gh CLI 없음 — Issue 생성 skip", file=sys.stderr)
        return None

    title = f"주간 개선 제안 ({report_path.stem})"
    body = report_path.read_text(encoding="utf-8")
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        print(f"[warn] gh issue create 실패: {exc.stderr}", file=sys.stderr)
        return None


def notify_slack(proposal_count: int, report_path: Path) -> None:
    """NOTIFY_SLACK_WEBHOOK이 있으면 Slack에 간단 알림. 없으면 skip."""
    url = os.environ.get("NOTIFY_SLACK_WEBHOOK")
    if not url:
        return
    try:
        import requests

        requests.post(
            url,
            json={
                "text": (
                    f"주간 개선 제안 {proposal_count}건 대기 중 -> "
                    f"{report_path.name}"
                )
            },
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[warn] Slack 알림 실패: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


def run(
    since_days: int,
    output: Path,
    dry_run: bool,
    create_issue: bool,
) -> int:
    print(f"[info] 실패 수집 시작 (since_days={since_days})", file=sys.stderr)
    failures = collect_failures(since_days=since_days)

    period = failures.get("period", {})
    period_label = f"{period.get('from', '')[:10]} ~ {period.get('to', '')[:10]}"

    if dry_run:
        proposal: dict[str, Any] = {
            "patterns": [],
            "proposed_updates": [],
            "opus_request_id": None,
            "confidence": 0.0,
            "notes": "dry-run: Opus 호출 생략",
        }
        print("[info] --dry-run: Opus 호출 생략", file=sys.stderr)
    else:
        print("[info] Opus 4.7 분석 시작", file=sys.stderr)
        proposal = analyze_and_propose(failures)

    report_md = render_report(failures, proposal, period_label)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report_md, encoding="utf-8")

    # 보조 산출물: 실패 수집 원본 JSON
    raw_path = output.with_suffix(".failures.json")
    raw_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    proposal_count = len(proposal.get("proposed_updates", []))
    print(
        f"[ok] report -> {output}  (제안 {proposal_count}건, dry_run={dry_run})",
        file=sys.stderr,
    )

    notify_slack(proposal_count, output)
    if create_issue and not dry_run and proposal_count > 0:
        url = create_github_issue(output, proposal)
        if url:
            print(f"[ok] GitHub Issue 생성: {url}", file=sys.stderr)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK_027 주간 자율 개선 루프")
    parser.add_argument("--since-days", type=int, default=7, help="최근 N일 실패 수집 (기본 7)")
    parser.add_argument(
        "--output",
        help="보고서 출력 경로 (기본 reports/improvement_YYYY-MM-DD.md)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Opus 호출 없이 수집+포맷만")
    parser.add_argument("--create-issue", action="store_true", help="gh CLI로 GitHub Issue 자동 생성")
    args = parser.parse_args()

    output = Path(args.output) if args.output else default_report_path()
    return run(
        since_days=args.since_days,
        output=output,
        dry_run=args.dry_run,
        create_issue=args.create_issue,
    )


if __name__ == "__main__":
    raise SystemExit(main())
