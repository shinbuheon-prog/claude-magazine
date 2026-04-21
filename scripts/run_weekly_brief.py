"""
주간 무료 브리프 자동 실행
사용법:
  python scripts/run_weekly_brief.py --topic "TOPIC" --dry-run
  python scripts/run_weekly_brief.py --topic "TOPIC" --publish
  python scripts/run_weekly_brief.py --topic "TOPIC" --sources src1.md src2.md --dry-run
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from pipeline.brief_generator import generate_brief, load_sources
from pipeline.draft_writer import write_section
from pipeline.ghost_client import create_post, send_newsletter

load_dotenv()

ROOT = Path(__file__).parent.parent
DRAFTS_DIR = ROOT / "drafts"
LOGS_DIR = ROOT / "logs"
DRAFTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def _has_anthropic_env() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _has_ghost_env() -> bool:
    return bool(os.getenv("GHOST_ADMIN_API_URL") and os.getenv("GHOST_ADMIN_API_KEY"))


def _render_html_from_markdown(markdown_text: str) -> str:
    paragraphs = [part.strip() for part in markdown_text.split("\n\n") if part.strip()]
    html_parts: list[str] = []
    for paragraph in paragraphs:
        if paragraph.startswith("# "):
            html_parts.append(f"<h1>{paragraph[2:].strip()}</h1>")
        elif paragraph.startswith("## "):
            html_parts.append(f"<h2>{paragraph[3:].strip()}</h2>")
        else:
            html_parts.append(f"<p>{paragraph.replace(chr(10), '<br/>')}</p>")
    return "\n".join(html_parts)


def publish_to_ghost(title: str, html_content: str, publish: bool) -> dict:
    """Ghost Admin API로 포스트 생성하고 필요 시 뉴스레터를 발송한다."""
    if not _has_ghost_env():
        status = "published" if publish else "draft"
        return {
            "post_id": "dry-run-post",
            "url": "",
            "status": status,
            "newsletter_id": "",
            "recipient_count": 0,
            "mode": "local-dry-run",
        }

    result = create_post(title, html_content, status="published" if publish else "draft")
    result["newsletter_id"] = ""
    result["recipient_count"] = 0
    if publish:
        newsletter_result = send_newsletter(result["post_id"])
        result.update(newsletter_result)
    return result


def _write_publish_log(topic: str, result: dict, mode: str, ts: str) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "ghost_post_id": result.get("post_id", ""),
        "ghost_url": result.get("url", ""),
        "mode": mode,
        "status": result.get("status", ""),
        "newsletter_id": result.get("newsletter_id", ""),
        "recipient_count": result.get("recipient_count", 0),
    }
    log_path = LOGS_DIR / f"publish_{ts}.json"
    log_path.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def _generate_brief_with_fallback(topic: str, source_bundle: str, force_dry_run: bool) -> dict:
    if force_dry_run:
        return generate_brief(topic, source_bundle, dry_run=True)

    try:
        return generate_brief(topic, source_bundle, dry_run=False)
    except Exception as exc:
        print(f"[warn] Claude 브리프 생성 실패, dry-run 샘플로 폴백: {exc}")
        return generate_brief(topic, source_bundle, dry_run=True)


def _write_section_with_fallback(brief: dict, section_name: str, source_bundle: str, force_dry_run: bool) -> str:
    if force_dry_run:
        return write_section(brief, section_name, source_bundle, dry_run=True)

    try:
        return write_section(brief, section_name, source_bundle, dry_run=False)
    except Exception as exc:
        print(f"[warn] 섹션 '{section_name}' 생성 실패, dry-run 샘플로 폴백: {exc}")
        return write_section(brief, section_name, source_bundle, dry_run=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="주간 브리프 실행")
    parser.add_argument("--topic", required=True, help="기사 주제")
    parser.add_argument("--sources", nargs="*", default=[], help="소스 파일 경로들")
    parser.add_argument("--dry-run", action="store_true", help="Ghost draft까지 생성")
    parser.add_argument("--publish", action="store_true", help="실제 발행 및 뉴스레터 발송")
    args = parser.parse_args()

    if args.dry_run == args.publish:
        parser.error("--dry-run 또는 --publish 중 하나만 지정하세요.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "publish" if args.publish else "dry-run"
    anthropic_dry_run = not _has_anthropic_env()
    source_bundle = load_sources(args.sources)

    print(f"=== 주간 브리프 시작: {args.topic} ===")
    if anthropic_dry_run:
        print("[info] ANTHROPIC_API_KEY가 없어 브리프/초안은 로컬 dry-run 샘플로 생성합니다.")
    if not _has_ghost_env():
        print("[info] Ghost 환경변수가 없어 게시 단계는 로컬 dry-run 결과로 기록합니다.")

    print("[1/3] 브리프 생성 중...")
    brief = _generate_brief_with_fallback(
        args.topic,
        source_bundle,
        force_dry_run=anthropic_dry_run,
    )
    brief_path = DRAFTS_DIR / f"brief_{ts}.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  제목 후보: {brief.get('working_title', '(없음)')}")
    print(f"  브리프 저장: {brief_path}")

    print("[2/3] 초안 생성 중...")
    outline = brief.get("outline", [])
    full_draft = f"# {brief.get('working_title', args.topic)}\n\n"
    for section in outline:
        section_name = section.get("section", "")
        print(f"  섹션: {section_name}")
        draft_section = _write_section_with_fallback(
            brief,
            section_name,
            source_bundle,
            force_dry_run=anthropic_dry_run,
        )
        if not draft_section.lstrip().startswith("## "):
            full_draft += f"## {section_name}\n\n"
        full_draft += f"{draft_section}\n\n"

    draft_path = DRAFTS_DIR / f"draft_{ts}.md"
    draft_path.write_text(full_draft, encoding="utf-8")
    print(f"  초안 저장: {draft_path}")

    print("[3/3] Ghost 게시 중...")
    html_content = _render_html_from_markdown(full_draft)
    try:
        result = publish_to_ghost(
            title=brief.get("working_title", args.topic),
            html_content=html_content,
            publish=args.publish,
        )
    except Exception as exc:
        result = {
            "post_id": "",
            "url": "",
            "status": "failed",
            "newsletter_id": "",
            "recipient_count": 0,
            "error": str(exc),
        }
    publish_log_path = _write_publish_log(args.topic, result, mode, ts)
    print(f"  결과: {result}")
    print(f"  발행 로그 저장: {publish_log_path}")
    print(f"=== 완료 ({mode}) ===")


if __name__ == "__main__":
    main()
