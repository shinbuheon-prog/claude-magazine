"""
주간 무료 브리프 자동 실행
사용법:
  python scripts/run_weekly_brief.py --topic "TOPIC" --dry-run   # 브리프+임시저장만
  python scripts/run_weekly_brief.py --topic "TOPIC" --publish   # 전체 발행
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.brief_generator import generate_brief, load_sources
from pipeline.draft_writer import write_section
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
DRAFTS_DIR = ROOT / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


def publish_to_ghost(title: str, html_content: str, dry_run: bool = True) -> dict:
    """Ghost Admin API로 포스트 생성"""
    try:
        import jwt, requests, time

        key = os.environ["GHOST_ADMIN_API_KEY"]
        api_url = os.environ["GHOST_ADMIN_API_URL"]
        kid, secret = key.split(":")
        iat = int(time.time())
        token = jwt.encode(
            {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
            bytes.fromhex(secret),
            algorithm="HS256",
            headers={"kid": kid},
        )
        headers = {"Authorization": f"Ghost {token}"}
        payload = {
            "posts": [{
                "title": title,
                "html": html_content,
                "status": "draft" if dry_run else "published",
                "visibility": "public",
            }]
        }
        r = requests.post(f"{api_url}/ghost/api/admin/posts/", json=payload, headers=headers)
        r.raise_for_status()
        post = r.json()["posts"][0]
        return {"post_id": post["id"], "url": post["url"], "status": post["status"]}
    except Exception as e:
        print(f"[Ghost 오류] {e}", file=sys.stderr)
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="주간 브리프 실행")
    parser.add_argument("--topic", required=True, help="기사 주제")
    parser.add_argument("--sources", nargs="*", default=[], help="소스 파일 경로들")
    parser.add_argument("--dry-run", action="store_true", help="Ghost 임시저장까지만 (발송 안 함)")
    parser.add_argument("--publish", action="store_true", help="실제 발행")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"=== 주간 브리프 시작: {args.topic} ===")

    # 1. 브리프 생성
    print("\n[1/3] 브리프 생성 중...")
    source_bundle = load_sources(args.sources)
    brief = generate_brief(args.topic, source_bundle)
    brief_path = DRAFTS_DIR / f"brief_{ts}.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"브리프 저장: {brief_path}")
    print(f"제목 후보: {brief.get('working_title', '(없음)')}")

    if args.dry_run and not args.publish:
        print("\n[dry-run] 브리프 생성 완료. Ghost 게시 생략.")
        return

    # 2. 섹션별 초안 생성 (outline 첫 2섹션만 MVP에서 자동 생성)
    print("\n[2/3] 초안 생성 중...")
    outline = brief.get("outline", [])
    full_draft = f"# {brief.get('working_title', args.topic)}\n\n"
    for section in outline[:2]:
        section_name = section.get("section", "")
        print(f"  섹션: {section_name}")
        draft_section = write_section(brief, section_name, source_bundle)
        full_draft += f"## {section_name}\n\n{draft_section}\n\n"

    draft_path = DRAFTS_DIR / f"draft_{ts}.md"
    draft_path.write_text(full_draft, encoding="utf-8")
    print(f"초안 저장: {draft_path}")

    # 3. Ghost 게시
    print("\n[3/3] Ghost 게시 중...")
    is_dry = not args.publish
    result = publish_to_ghost(
        title=brief.get("working_title", args.topic),
        html_content=f"<p>{full_draft}</p>",
        dry_run=is_dry,
    )
    print(f"Ghost 결과: {result}")
    print(f"\n=== 완료 ({'임시저장' if is_dry else '발행'}) ===")


if __name__ == "__main__":
    main()
