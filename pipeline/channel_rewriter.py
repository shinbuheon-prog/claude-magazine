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
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Windows UTF-8 출력 가드
if sys.platform == "win32" and not getattr(sys.stdout, "_cm_utf8", False):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SNS_DIR = ROOT / "web" / "public" / "sns"
SNS_PUBLIC_BASE = "/sns"
CARD_NEWS_LOG = LOGS_DIR / "card_news.jsonl"

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
CARD_NEWS_LAYOUTS = [f"layout_{idx}" for idx in range(1, 8)]


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


def _extract_title_and_lines(draft_text: str) -> tuple[str, list[str]]:
    title = "Claude Magazine"
    lines: list[str] = []
    for raw in draft_text.splitlines():
        stripped = raw.replace("\ufeff", "").strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = re.sub(r"\[src-[^\]]+\]|\(source_id:\s*[^)]+\)", "", stripped[2:]).strip()
            continue
        if stripped.startswith("#"):
            continue
        cleaned = re.sub(r"\[src-[^\]]+\]|\(source_id:\s*[^)]+\)", "", stripped).strip()
        if cleaned:
            lines.append(cleaned)
    return title, lines


def _recommended_slide_count(source_char_len: int) -> int:
    if source_char_len <= 500:
        return 5
    if source_char_len <= 1500:
        return 7
    return 10


def _chunk_lines(lines: list[str], target_chunks: int) -> list[list[str]]:
    if not lines:
        return [[] for _ in range(target_chunks)]
    chunk_size = max(1, len(lines) // target_chunks)
    chunks: list[list[str]] = []
    cursor = 0
    for _ in range(target_chunks - 1):
        next_cursor = min(len(lines), cursor + chunk_size)
        chunks.append(lines[cursor:next_cursor])
        cursor = next_cursor
    chunks.append(lines[cursor:])
    while len(chunks) < target_chunks:
        chunks.append([])
    return chunks


def _split_content_sentences(lines: list[str]) -> list[str]:
    sentences: list[str] = []
    for line in lines:
        parts = [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", line) if part.strip()]
        sentences.extend(parts)
    return sentences


def build_card_news_slides(draft_text: str, channel: str) -> dict[str, object]:
    title, lines = _extract_title_and_lines(draft_text)
    source_char_len = len(re.sub(r"\s+", "", draft_text))
    total_slides = _recommended_slide_count(source_char_len)
    body_count = max(1, total_slides - 2)
    sentences = _split_content_sentences(lines)
    chunks = _chunk_lines(sentences or lines, body_count)
    slides: list[dict[str, object]] = []

    slides.append({
        "idx": 1,
        "role": "hook",
        "layout": "layout_6",
        "tag": "Claude Magazine",
        "main_copy": title,
        "sub_copy": lines[0] if lines else "핵심 메시지를 먼저 붙잡는 카드",
        "highlight": "Hook",
        "footer": "@claude_magazine_kr",
    })

    for idx, chunk in enumerate(chunks, start=2):
        if idx == total_slides:
            break
        main_copy = chunk[0] if chunk else f"{idx-1}번째 핵심 포인트"
        extra = chunk[1:4] if chunk else []
        slides.append({
            "idx": idx,
            "role": "body",
            "layout": CARD_NEWS_LAYOUTS[(idx - 2) % len(CARD_NEWS_LAYOUTS)],
            "tag": "핵심 정리",
            "main_copy": main_copy,
            "sub_copy": " ".join(extra[:2]),
            "highlight": extra[2] if len(extra) > 2 else "",
            "footer": "@claude_magazine_kr",
        })

    slides.append({
        "idx": len(slides) + 1,
        "role": "cta",
        "layout": "layout_4",
        "tag": "다음 액션",
        "main_copy": "원문에서 전체 맥락을 확인하세요",
        "sub_copy": "저장해두고 실무에 바로 적용할 포인트만 다시 보세요.",
        "highlight": "Save / Share / Read",
        "footer": "@claude_magazine_kr",
    })

    return {
        "channel": channel,
        "format": "card-news",
        "slides": slides,
        "meta": {
            "total_slides": len(slides),
            "source_char_len": source_char_len,
        },
    }


def _log_card_news(payload: dict[str, object], request_id: str | None) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "channel": payload.get("channel"),
        "format": payload.get("format"),
        "total_slides": payload.get("meta", {}).get("total_slides") if isinstance(payload.get("meta"), dict) else None,
        "source_char_len": payload.get("meta", {}).get("source_char_len") if isinstance(payload.get("meta"), dict) else None,
    }
    with CARD_NEWS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _haiku_rewrite(draft_text: str, channel: str) -> str:
    """Haiku API 호출로 텍스트 재가공 (기존 로직)."""
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from pipeline.observability import log_usage, start_trace
    except ModuleNotFoundError:
        from observability import log_usage, start_trace  # type: ignore

    # TASK_033: provider 추상화
    try:
        from pipeline.claude_provider import get_provider
    except ModuleNotFoundError:
        from claude_provider import get_provider  # type: ignore

    provider = get_provider()

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

    trace = start_trace(name="channel_rewriting", model=f"haiku-via-{provider.name}")

    def _stream_print(chunk: str) -> None:
        try:
            print(chunk, end="", flush=True)
        except UnicodeEncodeError:
            pass

    result = provider.stream_complete(
        system=system_prompt,
        user=user_prompt,
        model_tier="haiku",
        max_tokens=2000,
        stream_callback=_stream_print,
    )
    print()
    result_text = result.text
    request_id = result.request_id
    input_tokens = result.input_tokens
    output_tokens = result.output_tokens

    log_usage(
        getattr(trace, "id", None),
        input_tokens,
        output_tokens,
        result.model or "claude-haiku-4-5-20251001",
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
    request_id: str | None = None
    if not skip_text:
        text_out = _haiku_rewrite(draft_text, channel)
        rewrite_logs = sorted(LOGS_DIR.glob(f"rewrite_{channel}_*.json"))
        if rewrite_logs:
            try:
                request_id = json.loads(rewrite_logs[-1].read_text(encoding="utf-8")).get("request_id")
            except Exception:
                request_id = None

    assets: list[dict] = []
    missing: list[str] = []
    recs: list[str] = []
    card_news_payload: dict[str, object] | None = None

    if post_slug:
        assets, missing = collect_channel_assets(channel, post_slug, month)
        recs = _build_recommendations(channel, missing, assets)

    if channel in {"sns", "instagram"}:
        card_news_payload = build_card_news_slides(draft_text, channel)
        try:
            try:
                from pipeline.editorial_lint import lint_card_news
            except ModuleNotFoundError:
                from editorial_lint import lint_card_news  # type: ignore
            lint = lint_card_news(card_news_payload["slides"], draft_text)  # type: ignore[arg-type]
            card_news_payload["meta"]["lint_result"] = "pass" if lint["can_publish"] else "fail"  # type: ignore[index]
            card_news_payload["meta"]["lint_items"] = lint["items"]  # type: ignore[index]
        except Exception:
            card_news_payload["meta"]["lint_result"] = "warn"  # type: ignore[index]
        slides = card_news_payload.get("slides", [])
        if not slides or slides[0].get("role") != "hook" or slides[-1].get("role") != "cta":
            raise ValueError("card-news slide schema invalid: hook/cta 누락")
        _log_card_news(card_news_payload, request_id)

    result = {
        "channel": channel,
        "text": text_out,
        "assets": assets,
        "missing_assets": missing,
        "recommendations": recs,
        "post_slug": post_slug,
        "month": month,
    }
    if card_news_payload is not None:
        result.update(card_news_payload)
    return result


def _print_assets_report(result: dict) -> None:
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
        draft_text = draft_path.read_text(encoding="utf-8-sig")

    skip_text = args.assets_report or args.dry_run
    if not args.json:
        print(f"=== Channel Rewriter ({args.channel}) ===")
    if not skip_text and not args.json:
        print("\n재가공 텍스트:")

    result = rewrite_for_channel(
        draft_text,
        args.channel,
        post_slug=args.post_slug,
        month=args.month,
        skip_text=skip_text,
    )

    # 자산 리포트
    if args.post_slug and not args.json:
        _print_assets_report(result)
    elif skip_text and not args.json:
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
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 누락 자산이 있으면 비-zero 반환은 하지 않음 (경고만) — 워크플로 계속 진행
    return 0


if __name__ == "__main__":
    sys.exit(main())
