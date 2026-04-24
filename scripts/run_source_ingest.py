"""
소스 자동 수집 CLI 진입점 (TASK_032)

매일 Cron으로 호출되어 config/feeds.yml의 RSS 피드들을 수집한다.

사용법:
    python scripts/run_source_ingest.py                    # 전체 피드
    python scripts/run_source_ingest.py --feed "Anthropic News"
    python scripts/run_source_ingest.py --dry-run
    python scripts/run_source_ingest.py --since-days 7
    python scripts/run_source_ingest.py --no-classify      # Haiku 호출 skip
"""
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가 (직접 실행 호환)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows UTF-8 강제
if sys.platform == "win32" and not getattr(sys.stdout, "_cm_utf8", False):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="소스 자동 수집 파이프라인")
    parser.add_argument(
        "--feeds-config",
        default="config/feeds.yml",
        help="피드 설정 YAML 경로 (기본: config/feeds.yml)",
    )
    parser.add_argument(
        "--feed",
        default=None,
        help="특정 피드만 수집 (name 일치)",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=None,
        help="state 무시하고 N일 전부터 재수집",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 등록 없이 조회만 (state 미갱신)",
    )
    parser.add_argument(
        "--no-classify",
        action="store_true",
        help="Haiku 분류 skip (비용 절감)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="결과를 JSON으로 출력",
    )
    args = parser.parse_args()

    print("=== 소스 자동 수집 ===\n")

    try:
        from pipeline.source_ingester import ingest_feeds
    except ImportError as exc:
        print(f"❌ source_ingester import 실패: {exc}", file=sys.stderr)
        print("   `pip install -r requirements.txt` 실행 후 재시도하세요.", file=sys.stderr)
        return 1

    try:
        result = ingest_feeds(
            feeds_path=args.feeds_config,
            since_days=args.since_days,
            feed_filter=args.feed,
            dry_run=args.dry_run,
            auto_classify=not args.no_classify,
        )
    except FileNotFoundError as exc:
        print(f"❌ 설정 파일 없음: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"❌ 런타임 오류: {exc}", file=sys.stderr)
        return 1

    if args.json:
        import json as _json
        print(_json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 텍스트 요약
    print("=== 결과 ===")
    print(f"  피드: {result['feeds_processed']}개")
    print(f"  조회: {result['entries_fetched']}건")
    print(f"  신규: {result['entries_new']}건")
    print(f"  기존: {result['entries_duplicate']}건")
    if result["dry_run"]:
        print("  (dry-run — 등록 안 함)")
    else:
        print(f"  등록 완료: {result['entries_registered']}건")

    error_count = sum(len(d.get("errors", [])) for d in result["details"])
    if error_count > 0:
        print(f"  ⚠️  오류: {error_count}건 (details 참고)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
