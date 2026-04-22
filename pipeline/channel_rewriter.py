"""
채널별 재가공기 (SNS·이메일 요약 + 카드뉴스 자산 번들링)
모델: claude-haiku-4-5 (저비용 고속)

사용법:
    # 기존: 텍스트 재가공만
    python pipeline/channel_rewriter.py --draft drafts/article.md --channel sns

    # 신규: 자산 체크만 (API 호출 없음)
    python pipeline/channel_rewriter.py --draft drafts/article.md --channel sns \
        --post-slug claude-4-launch --month 2026-05 --assets-report

    # 신규: 재가공 + 자산 번들링
    python pipeline/channel_rewriter.py --draft drafts/article.md --channel sns \
        --post-slug claude-4-launch --month 2026-05
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Windows UTF-8 출력 (fact_checker.py / check_covers.py 패턴)
# 중복 래핑 방지: 이미 utf-8 로 래핑된 경우 skip (import 시 stream close 로 인한
# "I/O operation on closed file" 방어)
if sys.platform == "win32":
    if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SNS_DIR = ROOT / "web" / "public" / "sns"
SNS_PUBLIC_BASE = "/sns"

CLAUDE_DESIGN_URL = "https://claude.ai/design"

CHANNEL_INSTRUCTIONS = {
    "sns": (
        "트위터/X 스레드 형식으로 재가공하라.\n"
        "첫 트윗은 후킹 문장 + 핵심 수치.\n"
        "이어지는 트윗은 2~3개, 각 280자 이내.\n"
        "마지막 트윗은 CTA (원문 링크 자리 표시).\n"
        "해시태그 2~3개 포함."
    ),
    "email": (
        "주간 뉴스레터 요약 섹션으로 재가공하라.\n"
        "제목(이메일 subject line), 리드 문장, 핵심 포인트 3개, 원문 링크 안내.\n"
        "총 150단어 이내."
    ),
    "linkedin": (
        "LinkedIn 포스트로 재가공하라.\n"
        "첫 2줄이 핵심 인사이트 (스크롤 없이 보임).\n"
        "본문 5~7줄, 비즈니스 독자 대상 톤.\n"
        "해시태그 3~5개."
    ),
    "twitter": (
        "트위터/X 스레드 형식으로 재가공하라.\n"
        "첫 트윗은 후킹 문장 + 핵심 수치.\n"
        "이어지는 트윗은 2~3개, 각 280자 이내.\n"
        "마지막 트윗은 CTA (원문 링크 자리 표시).\n"
        "해시태그 2~3개 포함."
    ),
    "instagram": (
        "Instagram 피드 캡션으로 재가공하라.\n"
        "첫 줄 후킹, 본문 3~5줄, 친근한 톤.\n"
        "해시태그 5~10개 (한국어·영어 섞어서)."
    ),
}

# 채널별 기대 자산 매핑 (TASK_023 명세)
CHANNEL_ASSETS = {
    "sns": [
        {"type": "card-01", "size": "1080x1080", "alt": "SNS 카드 1"},
        {"type": "card-02", "size": "1080x1080", "alt": "SNS 카드 2"},
        {"type": "card-03", "size": "1080x1080", "alt": "SNS 카드 3"},
        {"type": "og", "size": "1200x630", "alt": "Open Graph 이미지"},
        {"type": "quote", "size": "1080x1080", "alt": "인용 이미지"},
    ],
    "instagram": [
        {"type": "card-01", "size": "1080x1080", "alt": "Instagram 피드"},
        {"type": "story", "size": "1080x1920", "alt": "Instagram 스토리"},
        {"type": "quote", "size": "1080x1080", "alt": "Instagram 인용 이미지"},
    ],
    "linkedin": [
        {"type": "linkedin-header", "size": "1200x627", "alt": "LinkedIn 헤더"},
        {"type": "og", "size": "1200x630", "alt": "LinkedIn Open Graph"},
    ],
    "twitter": [
        {"type": "twitter-card", "size": "1200x675", "alt": "Twitter/X 카드"},
        {"type": "quote", "size": "1080x1080", "alt": "Twitter/X 인용 이미지"},
    ],
}


def _current_month() -> str:
    now = datetime.now()
    return f"{now.year}-{now.month:02d}"


def get_image_metadata(path: Path) -> dict:
    """Pillow 로 이미지 메타데이터 추출 (설치되어 있지 않으면 파일 크기만 반환)."""
    meta: dict = {}
    try:
        from PIL import Image  # lazy import
    except ModuleNotFoundError:
        meta["size"] = None
        meta["format"] = None
        meta["mode"] = None
        return meta

    try:
        with Image.open(path) as img:
            meta["size"] = f"{img.width}x{img.height}"
            meta["format"] = img.format
            meta["mode"] = img.mode
    except Exception as exc:  # noqa: BLE001
        meta["size"] = None
        meta["format"] = None
        meta["mode"] = None
        meta["error"] = str(exc)
    return meta


def _expected_filename(post_slug: str, asset_type: str) -> str:
    """post_slug 와 asset type 으로 파일명 생성.

    예: slug='claude-4-launch', type='card-01' → 'claude-4-launch-card-01.png'
    """
    return f"{post_slug}-{asset_type}.png"


def _load_license_map() -> dict:
    licenses_path = SNS_DIR / "licenses.json"
    if not licenses_path.exists():
        return {}
    try:
        data = json.loads(licenses_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def collect_channel_assets(
    channel: str,
    post_slug: str,
    month: str,
) -> tuple[list[dict], list[str]]:
    """채널 기대 자산 목록을 순회하며 존재 여부·메타데이터를 반환.

    반환: (assets, missing_assets)
    """
    if channel not in CHANNEL_ASSETS:
        return [], []

    month_dir = SNS_DIR / month
    licenses = _load_license_map()
    assets: list[dict] = []
    missing: list[str] = []

    for spec in CHANNEL_ASSETS[channel]:
        fname = _expected_filename(post_slug, spec["type"])
        public_path = f"{SNS_PUBLIC_BASE}/{month}/{fname}"
        license_key = f"{month}/{fname}"
        fs_path = month_dir / fname
        exists = fs_path.exists()
        license_meta = licenses.get(license_key, {}) if isinstance(licenses.get(license_key), dict) else {}

        entry: dict = {
            "path": public_path,
            "exists": exists,
            "size": spec["size"],       # 기대 사이즈 (spec)
            "alt": license_meta.get("alt") or spec["alt"],
            "type": spec["type"],
            "file_size_kb": 0,
        }

        if exists:
            entry["file_size_kb"] = int(round(fs_path.stat().st_size / 1024))
            meta = get_image_metadata(fs_path)
            actual_size = meta.get("size")
            if actual_size:
                entry["actual_size"] = actual_size
                if actual_size != spec["size"]:
                    entry["size_mismatch"] = True
            if meta.get("format"):
                entry["format"] = meta["format"]
        else:
            missing.append(public_path)

        if license_meta:
            entry["license"] = {
                "source": license_meta.get("source"),
                "created_at": license_meta.get("created_at"),
                "rights": license_meta.get("rights"),
            }

        assets.append(entry)

    return assets, missing


def _build_recommendations(
    channel: str,
    missing_assets: list[str],
    assets: list[dict],
) -> list[str]:
    recs: list[str] = []
    if missing_assets:
        recs.append(
            f"{len(missing_assets)}개 이미지 추가 제작 필요 "
            f"({', '.join(Path(p).name for p in missing_assets)})"
        )
        recs.append(f"Claude Design: {CLAUDE_DESIGN_URL}")
        recs.append("라이선스 등록: web/public/sns/licenses.json")
    size_mismatches = [a for a in assets if a.get("size_mismatch")]
    if size_mismatches:
        for a in size_mismatches:
            recs.append(
                f"사이즈 불일치: {Path(a['path']).name} — "
                f"기대 {a['size']}, 실제 {a.get('actual_size')}"
            )
    return recs


def _haiku_rewrite(draft_text: str, channel: str) -> str:
    """Haiku API 호출로 텍스트 재가공 (기존 로직)."""
    import anthropic  # lazy import so --assets-report 모드는 의존성 없음
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from pipeline.observability import log_usage, start_trace
    except ModuleNotFoundError:
        from observability import log_usage, start_trace  # type: ignore

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system_prompt = (
        "당신은 SNS·이메일 콘텐츠 전문가다.\n"
        "한국어로 작성하고, 마케팅 문구와 과장은 금지한다.\n"
        "원문의 핵심 사실만 유지하고, 링크·출처를 항상 포함한다."
    )

    user_prompt = (
        f"다음 기사 초안을 {channel} 형식으로 재가공하라.\n\n"
        f"<instructions>\n{CHANNEL_INSTRUCTIONS[channel]}\n</instructions>\n\n"
        f"<draft>\n{draft_text}\n</draft>"
    )

    result_text = ""
    request_id = None
    input_tokens = 0
    output_tokens = 0
    trace = start_trace(name="channel_rewriting", model="claude-haiku-4-5-20251001")

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text
            print(text, end="", flush=True)
        final = stream.get_final_message()
        request_id = getattr(final, "_request_id", None)
        input_tokens = final.usage.input_tokens
        output_tokens = final.usage.output_tokens

    print()
    log_usage(
        getattr(trace, "id", None),
        input_tokens,
        output_tokens,
        "claude-haiku-4-5-20251001",
        request_id=request_id,
    )

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-haiku-4-5-20251001",
        "channel": channel,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    log_file = LOGS_DIR / f"rewrite_{channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} -> {log_file.name}", file=sys.stderr)

    return result_text


def rewrite_for_channel(
    draft_text: str,
    channel: str,
    post_slug: str = "",
    month: str | None = None,
    skip_text: bool = False,
) -> dict:
    """채널별 텍스트 재가공 + 자산 번들링.

    반환: {
        "channel": str,
        "text": str,                  # skip_text=True 면 빈 문자열
        "assets": [ {path, exists, size, file_size_kb, alt, ...}, ... ],
        "missing_assets": [str],
        "recommendations": [str],
    }

    하위 호환:
        post_slug 가 비어 있으면 자산 체크는 스킵하고 텍스트만 재가공 후
        단순 dict 반환 (assets=[], missing_assets=[], recommendations=[]).
    """
    if channel not in CHANNEL_INSTRUCTIONS:
        raise ValueError(
            f"지원하지 않는 채널: {channel}. 지원: {list(CHANNEL_INSTRUCTIONS.keys())}"
        )

    month = month or _current_month()

    text_out = ""
    if not skip_text:
        text_out = _haiku_rewrite(draft_text, channel)

    assets: list[dict] = []
    missing: list[str] = []
    recs: list[str] = []

    if post_slug:
        assets, missing = collect_channel_assets(channel, post_slug, month)
        recs = _build_recommendations(channel, missing, assets)

    return {
        "channel": channel,
        "text": text_out,
        "assets": assets,
        "missing_assets": missing,
        "recommendations": recs,
        "post_slug": post_slug,
        "month": month,
    }


def _print_assets_report(result: dict) -> None:
    channel = result["channel"]
    post_slug = result.get("post_slug") or "(no-slug)"
    month = result.get("month")
    print(f"\n자산 체크 (web/public/sns/{month}/{post_slug}-*):")
    if not result["assets"]:
        print("  [INFO] 이 채널에 정의된 기대 자산이 없습니다.")
        return
    for a in result["assets"]:
        name = Path(a["path"]).name
        if a["exists"]:
            actual = a.get("actual_size") or a["size"]
            mark = "✅"
            mismatch = " (사이즈 불일치!)" if a.get("size_mismatch") else ""
            print(
                f"  {mark} {name}  ({actual}, {a['file_size_kb']}KB){mismatch}  "
                f"alt=\"{a['alt']}\""
            )
        else:
            print(f"  ❌ {name}  (미존재, 기대 {a['size']})")

    if result["recommendations"]:
        print("\n권고:")
        for r in result["recommendations"]:
            print(f"  - {r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="채널별 재가공기 + 카드뉴스 자산 번들링")
    parser.add_argument("--draft", required=True, help="초안 마크다운 파일 경로")
    parser.add_argument(
        "--channel",
        required=True,
        choices=list(CHANNEL_INSTRUCTIONS.keys()),
    )
    parser.add_argument("--out", help="출력 파일 경로 (생략 시 stdout)")
    parser.add_argument(
        "--post-slug",
        default="",
        help="자산 파일명 매칭용 slug (예: claude-4-launch)",
    )
    parser.add_argument(
        "--month",
        default=None,
        metavar="YYYY-MM",
        help="월 지정 (없으면 현재월)",
    )
    parser.add_argument(
        "--assets-report",
        action="store_true",
        help="자산 존재 여부만 빠르게 출력 (텍스트 재가공 skip · API 호출 없음)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="결과를 JSON 으로 stdout 에 출력",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="--assets-report 와 동일 (API 호출 없이 자산 체크만)",
    )
    args = parser.parse_args()

    # draft 는 assets-report 모드에서도 경로 인자로만 쓰이므로 존재하지 않아도 스킵 허용
    draft_path = Path(args.draft)
    if not args.assets_report and not args.dry_run and not draft_path.exists():
        print(f"[FAIL] draft 파일이 존재하지 않음: {draft_path}", file=sys.stderr)
        return 1
    draft_text = ""
    if draft_path.exists():
        draft_text = draft_path.read_text(encoding="utf-8")

    print(f"=== Channel Rewriter ({args.channel}) ===")

    skip_text = args.assets_report or args.dry_run
    if not skip_text:
        print("\n재가공 텍스트:")

    result = rewrite_for_channel(
        draft_text,
        args.channel,
        post_slug=args.post_slug,
        month=args.month,
        skip_text=skip_text,
    )

    # 자산 리포트
    if args.post_slug:
        _print_assets_report(result)
    elif skip_text:
        print("\n[INFO] --post-slug 가 지정되지 않아 자산 체크를 건너뜁니다.")

    # 파일 출력
    if args.out:
        out_path = Path(args.out)
        if args.json:
            out_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            out_path.write_text(result["text"], encoding="utf-8")
        print(f"\n저장 완료: {out_path}", file=sys.stderr)

    if args.json and not args.out:
        print("\n=== JSON ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 누락 자산이 있으면 비-zero 반환은 하지 않음 (경고만) — 워크플로 계속 진행
    return 0


if __name__ == "__main__":
    sys.exit(main())
