"""
Claude Magazine 월간 커버 드롭인 검증 스크립트 (TASK_021)

체크 항목:
  1. web/public/covers/default.png 존재 (필수)
  2. licenses.json 의 모든 파일이 실제 존재하는지
  3. 실제 파일 중 licenses.json 에 누락된 것 경고
  4. 다음 월(YYYY-MM) 커버 등록 여부 체크

사용법:
    python scripts/check_covers.py
    python scripts/check_covers.py --strict     # 실패/경고가 하나라도 있으면 exit 1
    python scripts/check_covers.py --month 2026-06

종료 코드:
    0 — 통과 (또는 strict 가 아니면 경고만)
    1 — 필수 체크 실패 (default.png 누락, JSON 파싱 오류 등) 또는 strict 모드
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

# Windows 환경 UTF-8 출력 (fact_checker.py / check_env.py 패턴)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
COVERS_DIR = ROOT / "web" / "public" / "covers"
LICENSES_FILE = COVERS_DIR / "licenses.json"
DEFAULT_COVER = COVERS_DIR / "default.png"

# YYYY-MM.png / YYYY-MM@2x.png / YYYY-MM-variant-*.png 모두 매칭
MONTHLY_RE = re.compile(r"^(\d{4})-(\d{2})(?:@2x|-variant-[A-Za-z0-9_-]+)?\.(png|webp|jpg|jpeg)$")
BASE_MONTHLY_RE = re.compile(r"^(\d{4})-(\d{2})\.(png|webp|jpg|jpeg)$")

# 라이선스 필수 필드
REQUIRED_LICENSE_FIELDS = ("source", "created_at", "rights")


# ── 색상 아이콘 ───────────────────────────────────────
ICON_PASS = "[PASS]"
ICON_WARN = "[WARN]"
ICON_FAIL = "[FAIL]"
ICON_INFO = "[INFO]"


def next_month(ref: date) -> str:
    """기준일 다음 달을 YYYY-MM 으로 반환"""
    if ref.month == 12:
        return f"{ref.year + 1}-01"
    return f"{ref.year}-{ref.month + 1:02d}"


def list_cover_files() -> list[Path]:
    if not COVERS_DIR.is_dir():
        return []
    return sorted(p for p in COVERS_DIR.iterdir() if p.is_file() and MONTHLY_RE.match(p.name))


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="월간 커버 드롭인 검증 (TASK_021)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="경고가 하나라도 있으면 exit 1",
    )
    parser.add_argument(
        "--month",
        metavar="YYYY-MM",
        help="체크할 '다음 월' 을 지정 (기본: 오늘 기준 다음 달)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("=== Claude Magazine 커버 이미지 체크 (TASK_021) ===")
    print(f"디렉토리: {COVERS_DIR}")
    print()

    fail_count = 0
    warn_count = 0
    pass_count = 0

    # ── 1. default.png 존재 ────────────────────────────
    print("[1/4] default.png 존재 확인")
    if DEFAULT_COVER.exists():
        size_kb = DEFAULT_COVER.stat().st_size / 1024
        print(f"  {ICON_PASS} {DEFAULT_COVER.name} ({size_kb:.1f} KB)")
        pass_count += 1
    else:
        print(f"  {ICON_FAIL} {DEFAULT_COVER} 누락 — fallback 동작 불가")
        print(f"         해결: 800×550px 플레이스홀더를 {DEFAULT_COVER} 에 저장")
        fail_count += 1
    print()

    # ── 2. licenses.json 로드 + 파일 존재 교차 검증 ────
    print("[2/4] licenses.json ↔ 실제 파일 교차 검증")
    licenses, err = load_licenses()
    if err:
        print(f"  {ICON_FAIL} {err}")
        print(f"         해결: {LICENSES_FILE} 를 유효한 JSON object 로 생성 (빈 객체 '{{}}' 도 가능)")
        fail_count += 1
    else:
        if not licenses:
            print(f"  {ICON_INFO} licenses.json 이 비어 있음 (등록된 이미지 없음)")
        missing_files: list[str] = []
        missing_fields: list[tuple[str, list[str]]] = []
        for fname, meta in licenses.items():
            fpath = COVERS_DIR / fname
            if not fpath.exists():
                missing_files.append(fname)
                continue
            if not isinstance(meta, dict):
                missing_fields.append((fname, ["(meta 가 object 가 아님)"]))
                continue
            lacking = [f for f in REQUIRED_LICENSE_FIELDS if not meta.get(f)]
            if lacking:
                missing_fields.append((fname, lacking))
        if missing_files:
            for m in missing_files:
                print(f"  {ICON_FAIL} licenses.json 에 기록됐으나 파일 없음: {m}")
            fail_count += 1
        if missing_fields:
            for fname, fields in missing_fields:
                print(f"  {ICON_WARN} {fname}: 필수 필드 누락/형식 오류 → {', '.join(fields)}")
            warn_count += 1
        if not missing_files and not missing_fields and licenses:
            print(f"  {ICON_PASS} {len(licenses)}개 엔트리 모두 파일 존재 · 필수 필드 OK")
            pass_count += 1
        elif not licenses:
            pass_count += 1  # 빈 객체는 통과로 간주
    print()

    # ── 3. 실제 파일 중 licenses.json 에 없는 것 ───────
    print("[3/4] 실제 파일 중 licenses.json 누락 탐지")
    actual_files = list_cover_files()
    licensed_names = set(licenses.keys()) if isinstance(licenses, dict) else set()
    unlicensed = [p.name for p in actual_files if p.name not in licensed_names]
    if not actual_files:
        print(f"  {ICON_INFO} 월별 커버 파일이 없음 (default.png 만으로 운영 중)")
        pass_count += 1
    elif unlicensed:
        for name in unlicensed:
            print(f"  {ICON_WARN} {name} — licenses.json 에 라이선스 정보 미기록")
        print(f"         해결: {LICENSES_FILE} 에 source/created_at/rights 필드 추가")
        warn_count += 1
    else:
        print(f"  {ICON_PASS} {len(actual_files)}개 파일 모두 licenses.json 에 기록됨")
        pass_count += 1
    print()

    # ── 4. 다음 월 커버 존재 여부 ──────────────────────
    print("[4/4] 다음 월 커버 등록 여부")
    target_month = args.month or next_month(date.today())
    if not re.match(r"^\d{4}-\d{2}$", target_month):
        print(f"  {ICON_FAIL} --month 형식 오류: {target_month!r} (YYYY-MM 필요)")
        fail_count += 1
    else:
        candidates = [
            COVERS_DIR / f"{target_month}.png",
            COVERS_DIR / f"{target_month}.webp",
            COVERS_DIR / f"{target_month}.jpg",
            COVERS_DIR / f"{target_month}.jpeg",
        ]
        found = next((c for c in candidates if c.exists()), None)
        if found:
            print(f"  {ICON_PASS} {target_month} 커버 등록됨: {found.name}")
            pass_count += 1
        else:
            print(f"  {ICON_WARN} {target_month} 커버 미등록 — 렌더링 시 default.png 로 폴백")
            print(f"         해결: Claude Design 에서 커버 제작 후 {target_month}.png 저장")
            warn_count += 1
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
