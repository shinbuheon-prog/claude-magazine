"""
Claude Magazine SNS 카드뉴스 자산 검증 스크립트 (TASK_023)

체크 항목:
  1. web/public/sns/licenses.json 로드 (빈 객체여도 OK)
  2. licenses.json 의 모든 파일이 실제 존재하는지 (누락 경고)
  3. 실제 파일 중 licenses.json 에 없는 고아 파일 경고
  4. --post-slug 지정 시 해당 포스트 자산만 필터링 후 채널별 기대 자산 존재 여부 리포트

사용법:
    python scripts/check_sns_assets.py --month 2026-05
    python scripts/check_sns_assets.py --month 2026-05 --post-slug claude-4-launch
    python scripts/check_sns_assets.py --month 2026-05 --strict

종료 코드:
    0 — 통과 (또는 strict 가 아니면 경고만)
    1 — 필수 체크 실패 (licenses.json 파싱 오류 등) 또는 strict 모드에서 경고 발생
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

# Windows UTF-8 출력 (fact_checker.py / check_covers.py 패턴)
# 중복 래핑 방지: 이미 utf-8 로 래핑된 경우 skip
if sys.platform == "win32":
    if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SNS_DIR = ROOT / "web" / "public" / "sns"
LICENSES_FILE = SNS_DIR / "licenses.json"

# channel_rewriter 의 채널 자산 매핑 재사용 (동일 경로 컨벤션 유지)
try:
    sys.path.insert(0, str(ROOT))
    from pipeline.channel_rewriter import CHANNEL_ASSETS, CLAUDE_DESIGN_URL
except Exception:  # noqa: BLE001
    CHANNEL_ASSETS = {}
    CLAUDE_DESIGN_URL = "https://claude.ai/design"

MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
REQUIRED_LICENSE_FIELDS = ("source", "created_at", "rights")

ICON_PASS = "[PASS]"
ICON_WARN = "[WARN]"
ICON_FAIL = "[FAIL]"
ICON_INFO = "[INFO]"


def load_licenses() -> tuple[dict, str | None]:
    if not LICENSES_FILE.exists():
        return {}, f"{LICENSES_FILE} 가 존재하지 않음"
    try:
        data = json.loads(LICENSES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"JSON 파싱 실패: {exc}"
    if not isinstance(data, dict):
        return {}, f"licenses.json 이 object 가 아님 (type={type(data).__name__})"
    return data, None


def list_sns_files(month_dir: Path) -> list[Path]:
    if not month_dir.is_dir():
        return []
    return sorted(
        p for p in month_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"}
    )


def filter_by_slug(files: list[Path], post_slug: str) -> list[Path]:
    prefix = f"{post_slug}-"
    return [p for p in files if p.name.startswith(prefix)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SNS 카드뉴스 자산 검증 (TASK_023)"
    )
    parser.add_argument(
        "--month",
        required=True,
        metavar="YYYY-MM",
        help="검사할 월 (예: 2026-05)",
    )
    parser.add_argument(
        "--post-slug",
        default=None,
        help="특정 포스트 자산만 필터링 (예: claude-4-launch)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="경고가 하나라도 있으면 exit 1",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일시스템 변경 없이 리포트만 (현재 구현은 항상 read-only)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not MONTH_RE.match(args.month):
        print(f"[FAIL] --month 형식 오류: {args.month!r} (YYYY-MM 필요)", file=sys.stderr)
        return 1

    month_dir = SNS_DIR / args.month

    print("=== Claude Magazine SNS 자산 체크 (TASK_023) ===")
    print(f"디렉토리: {month_dir}")
    if args.post_slug:
        print(f"필터: post-slug = {args.post_slug}")
    print()

    fail_count = 0
    warn_count = 0
    pass_count = 0

    # ── 1. licenses.json 로드 ────────────────────────────
    print("[1/4] licenses.json 로드")
    licenses, err = load_licenses()
    if err:
        print(f"  {ICON_FAIL} {err}")
        print(
            f"         해결: {LICENSES_FILE} 를 유효한 JSON object 로 생성 "
            f"(빈 객체 '{{}}' 도 가능)"
        )
        fail_count += 1
        return 1
    if not licenses:
        print(f"  {ICON_INFO} licenses.json 이 비어 있음 (등록된 이미지 없음)")
    else:
        print(f"  {ICON_PASS} licenses.json 로드 OK ({len(licenses)}개 엔트리)")
    pass_count += 1
    print()

    # ── 2. 월별 폴더 존재 확인 ────────────────────────────
    print(f"[2/4] 월별 폴더 존재 확인: {args.month}/")
    if not month_dir.is_dir():
        print(f"  {ICON_WARN} {month_dir} 가 존재하지 않음 — 아직 이번 달 자산이 없습니다.")
        print(f"         해결: Claude Design({CLAUDE_DESIGN_URL}) 으로 자산 제작 후 업로드")
        warn_count += 1
        actual_files: list[Path] = []
    else:
        actual_files = list_sns_files(month_dir)
        if args.post_slug:
            actual_files = filter_by_slug(actual_files, args.post_slug)
        if not actual_files:
            scope = f"post-slug={args.post_slug}" if args.post_slug else "전체"
            print(f"  {ICON_INFO} {scope} 해당 파일 없음")
        else:
            print(f"  {ICON_PASS} {len(actual_files)}개 파일 발견")
            for p in actual_files:
                size_kb = p.stat().st_size / 1024
                print(f"         {p.name} ({size_kb:.1f} KB)")
            pass_count += 1
    print()

    # ── 3. licenses.json ↔ 실제 파일 교차 검증 ──────────
    print("[3/4] licenses.json <-> 실제 파일 교차 검증")
    # licenses.json 의 key 는 "YYYY-MM/filename.png" 상대 경로
    scope_prefix = f"{args.month}/"
    if args.post_slug:
        def scope_filter(k: str) -> bool:
            return k.startswith(scope_prefix) and Path(k).name.startswith(
                f"{args.post_slug}-"
            )
    else:
        def scope_filter(k: str) -> bool:
            return k.startswith(scope_prefix)

    scoped_licenses = {k: v for k, v in licenses.items() if scope_filter(k)}
    missing_files: list[str] = []
    missing_fields: list[tuple[str, list[str]]] = []

    for key, meta in scoped_licenses.items():
        fpath = SNS_DIR / key  # SNS_DIR + "YYYY-MM/filename.png"
        if not fpath.exists():
            missing_files.append(key)
            continue
        if not isinstance(meta, dict):
            missing_fields.append((key, ["(meta 가 object 가 아님)"]))
            continue
        lacking = [f for f in REQUIRED_LICENSE_FIELDS if not meta.get(f)]
        if lacking:
            missing_fields.append((key, lacking))

    if missing_files:
        for m in missing_files:
            print(f"  {ICON_FAIL} licenses.json 에 기록됐으나 파일 없음: {m}")
        fail_count += 1
    if missing_fields:
        for key, fields in missing_fields:
            print(f"  {ICON_WARN} {key}: 필수 필드 누락/형식 오류 -> {', '.join(fields)}")
        warn_count += 1
    if not missing_files and not missing_fields and scoped_licenses:
        print(
            f"  {ICON_PASS} {len(scoped_licenses)}개 엔트리 모두 파일 존재 · 필수 필드 OK"
        )
        pass_count += 1
    elif not scoped_licenses:
        print(f"  {ICON_INFO} 해당 범위의 라이선스 엔트리 없음")

    # 고아 파일 (실제 파일인데 licenses.json 에 없음)
    licensed_keys = set(scoped_licenses.keys())
    orphans: list[str] = []
    for p in actual_files:
        key = f"{args.month}/{p.name}"
        if key not in licensed_keys:
            orphans.append(key)
    if orphans:
        for o in orphans:
            print(f"  {ICON_WARN} {o} — licenses.json 에 라이선스 정보 미기록 (고아 파일)")
        print(f"         해결: {LICENSES_FILE} 에 source/created_at/rights 필드 추가")
        warn_count += 1
    print()

    # ── 4. 채널별 기대 자산 존재 여부 (--post-slug 필요) ─
    print("[4/4] 채널별 기대 자산 존재 여부")
    if not args.post_slug:
        print(f"  {ICON_INFO} --post-slug 가 지정되지 않아 기대 자산 체크를 건너뜁니다.")
    elif not CHANNEL_ASSETS:
        print(f"  {ICON_WARN} channel_rewriter.CHANNEL_ASSETS 를 import 하지 못했습니다.")
        warn_count += 1
    else:
        any_missing = False
        for channel, specs in CHANNEL_ASSETS.items():
            print(f"  · 채널 {channel}:")
            for spec in specs:
                fname = f"{args.post_slug}-{spec['type']}.png"
                fpath = month_dir / fname
                if fpath.exists():
                    size_kb = fpath.stat().st_size / 1024
                    print(
                        f"      {ICON_PASS} {fname} ({spec['size']}, {size_kb:.1f} KB) "
                        f"alt=\"{spec['alt']}\""
                    )
                else:
                    print(f"      {ICON_WARN} {fname} (미존재, 기대 {spec['size']})")
                    any_missing = True
        if any_missing:
            print(f"         해결: Claude Design({CLAUDE_DESIGN_URL}) 으로 누락 자산 제작")
            warn_count += 1
        else:
            pass_count += 1
    print()

    # ── 집계 ───────────────────────────────────────────
    print(f"=== 결과: {pass_count} 통과 / {fail_count} 실패 / {warn_count} 경고 ===")

    if fail_count > 0:
        return 1
    if args.strict and warn_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
