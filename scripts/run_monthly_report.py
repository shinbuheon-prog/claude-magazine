"""
월간 딥리서치 리포트 실행 (Opus 4.7 팩트체크 포함)
사용법: python scripts/run_monthly_report.py --topic "TOPIC" [--publish]
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.brief_generator import generate_brief, load_sources
from pipeline.draft_writer import write_section
from pipeline.fact_checker import run_factcheck, load_sources_for_article
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
DRAFTS_DIR = ROOT / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="월간 딥리서치 리포트")
    parser.add_argument("--topic", required=True, help="리포트 주제")
    parser.add_argument("--sources", nargs="*", default=[], help="소스 파일 경로들")
    parser.add_argument("--article-id", help="출처 레지스트리 기사 ID")
    parser.add_argument("--publish", action="store_true", help="팩트체크 후 발행")
    parser.add_argument("--strict-diversity", action="store_true", help="소스 다양성 실패 시 중단")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"=== 월간 딥리서치 시작: {args.topic} ===")

    # 1. 브리프 생성
    print("\n[1/4] 브리프 생성 중...")
    source_bundle = load_sources(args.sources)
    brief = generate_brief(
        args.topic,
        source_bundle,
        article_id=args.article_id or "",
        strict_diversity=args.strict_diversity,
    )
    brief_path = DRAFTS_DIR / f"monthly_brief_{ts}.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"브리프 저장: {brief_path}")

    # 2. 전체 섹션 초안 생성
    print("\n[2/4] 전체 섹션 초안 생성 중...")
    outline = brief.get("outline", [])
    full_draft = f"# {brief.get('working_title', args.topic)}\n\n"
    for section in outline:
        section_name = section.get("section", "")
        print(f"  섹션: {section_name}")
        draft_section = write_section(brief, section_name, source_bundle)
        full_draft += f"## {section_name}\n\n{draft_section}\n\n"

    draft_path = DRAFTS_DIR / f"monthly_draft_{ts}.md"
    draft_path.write_text(full_draft, encoding="utf-8")
    print(f"초안 저장: {draft_path}")

    # 3. Opus 4.7 팩트체크
    print("\n[3/4] 팩트체크 실행 중 (Opus 4.7)...")
    source_for_check = load_sources_for_article(args.article_id)
    factcheck_result = run_factcheck(full_draft, source_for_check)
    factcheck_path = DRAFTS_DIR / f"monthly_factcheck_{ts}.md"
    factcheck_path.write_text(factcheck_result, encoding="utf-8")
    print(f"팩트체크 저장: {factcheck_path}")

    # 4. 편집자 최종 확인 안내
    print("\n[4/4] 편집자 최종 확인 필요")
    print(f"  초안: {draft_path}")
    print(f"  팩트체크: {factcheck_path}")
    print("\n편집자가 Ghost Admin에서 최종 확인 후 발행하세요.")
    print("=== 월간 리포트 자동화 완료 ===")


if __name__ == "__main__":
    main()
