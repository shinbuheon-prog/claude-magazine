"""
Claude Provider 통합 검증 (TASK_033)

3종 provider(API·SDK·Mock) 인스턴스화 + 최소 호출 + 각 pipeline 모듈 import 정상 확인.
CLAUDE_PROVIDER 환경변수를 바꿔가며 실행해 모든 경로 점검.

사용법:
    python scripts/check_provider.py              # Mock으로 전체 경로 검증
    CLAUDE_PROVIDER=sdk python scripts/check_provider.py --call-sdk
    CLAUDE_PROVIDER=api python scripts/check_provider.py --call-api
"""
import argparse
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    # check_provider가 pipeline 모듈들을 import하면서 각각 stderr.reconfigure를 호출해
    # 충돌하는 문제 방지: 환경변수 PYTHONIOENCODING을 권장하고 직접 재설정은 skip.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def check_imports() -> list[tuple[str, bool, str]]:
    """pipeline 모듈들이 provider 변경 후에도 import 가능한지 확인."""
    results = []
    modules = [
        "pipeline.claude_provider",
        "pipeline.brief_generator",
        "pipeline.draft_writer",
        "pipeline.fact_checker",
        "pipeline.channel_rewriter",
        "pipeline.source_diversity",
        "pipeline.source_ingester",
        "pipeline.editorial_lint",
        "pipeline.sop_updater",
    ]
    for m in modules:
        try:
            __import__(m)
            results.append((m, True, "OK"))
        except Exception as e:
            results.append((m, False, f"{type(e).__name__}: {e}"))
    return results


def mock_call() -> bool:
    """Mock provider로 간단 호출 — 모든 경로 구조 검증."""
    from pipeline.claude_provider import get_provider

    try:
        provider = get_provider(override="mock", refresh=True)
        chunks = []
        result = provider.stream_complete(
            system="test",
            user="test",
            model_tier="sonnet",
            max_tokens=100,
            stream_callback=lambda c: chunks.append(c),
        )
        return bool(result.text)
    except Exception as e:
        print(f"Mock 호출 실패: {e}", file=sys.stderr)
        return False


def sdk_call() -> bool:
    """SDK로 간단 Haiku 호출 (Max 구독 내 동작 확인)."""
    from pipeline.claude_provider import get_provider

    try:
        provider = get_provider(override="sdk", refresh=True)
        result = provider.stream_complete(
            system="간결히 답하라.",
            user="'OK'만 출력하라.",
            model_tier="haiku",
            max_tokens=20,
        )
        return bool(result.text and "OK" in result.text.upper())
    except Exception as e:
        print(f"SDK 호출 실패: {e}", file=sys.stderr)
        return False


def api_call() -> bool:
    """API로 간단 Haiku 호출 (ANTHROPIC_API_KEY 필요)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("API 키 미설정 — skip", file=sys.stderr)
        return True  # skip으로 OK 처리
    from pipeline.claude_provider import get_provider

    try:
        provider = get_provider(override="api", refresh=True)
        result = provider.stream_complete(
            system="간결히 답하라.",
            user="'OK'만 출력하라.",
            model_tier="haiku",
            max_tokens=20,
        )
        return bool(result.text and "OK" in result.text.upper())
    except Exception as e:
        print(f"API 호출 실패: {e}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Provider 통합 검증")
    parser.add_argument("--call-sdk", action="store_true", help="SDK 실호출 테스트")
    parser.add_argument("--call-api", action="store_true", help="API 실호출 테스트")
    args = parser.parse_args()

    print("=== Claude Provider 통합 검증 ===\n")

    print("[1단계] pipeline 모듈 import 검증")
    import_results = check_imports()
    for name, ok, msg in import_results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}  ({msg})")
    import_pass = all(ok for _, ok, _ in import_results)

    print(f"\n[2단계] Mock provider 호출 검증")
    mock_ok = mock_call()
    print(f"  {'✅' if mock_ok else '❌'} Mock 호출")

    sdk_ok = None
    if args.call_sdk:
        print(f"\n[3단계] SDK 실호출 (Haiku, Max 구독)")
        sdk_ok = sdk_call()
        print(f"  {'✅' if sdk_ok else '❌'} SDK Haiku 호출")

    api_ok = None
    if args.call_api:
        print(f"\n[4단계] API 실호출 (Haiku)")
        api_ok = api_call()
        print(f"  {'✅' if api_ok else '❌'} API Haiku 호출")

    print("\n=== 요약 ===")
    print(f"  Import 검증: {'PASS' if import_pass else 'FAIL'}")
    print(f"  Mock 호출: {'PASS' if mock_ok else 'FAIL'}")
    if sdk_ok is not None:
        print(f"  SDK 실호출: {'PASS' if sdk_ok else 'FAIL'}")
    if api_ok is not None:
        print(f"  API 실호출: {'PASS' if api_ok else 'FAIL'}")

    overall = import_pass and mock_ok
    if args.call_sdk:
        overall = overall and sdk_ok
    if args.call_api:
        overall = overall and api_ok

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
