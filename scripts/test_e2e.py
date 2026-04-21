"""
주간 브리프 E2E 스모크 테스트 (TASK_013)

파이프라인 전체(브리프 -> 초안 -> 팩트체크 -> Ghost 드래프트)를 실제 API 호출 없이
mock 으로 검증한다. --live 모드는 check_env.py --strict 통과 시에만 실제 API를 호출한다.

사용법:
    python scripts/test_e2e.py                   # mock, 전체 4 단계
    python scripts/test_e2e.py --step brief      # 특정 단계만
    python scripts/test_e2e.py --live            # 실제 API (비용 주의)

exit code: 전체 통과 0, 하나라도 실패 1
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Windows 환경에서 한국어/특수문자 출력을 위한 UTF-8 강제 설정.
# fact_checker.py 는 import 시점에 `sys.stdout = TextIOWrapper(sys.stdout.buffer, ...)` 로
# 스트림 객체 자체를 교체하므로, 우리가 동일한 방식으로 먼저 래핑하면 두 번째 래퍼가
# 첫 번째 래퍼의 버퍼를 참조하다가 GC 시점에 `lost sys.stderr` 에러를 낸다.
# -> 객체를 교체하지 않고 `reconfigure(encoding=...)` 로 인코딩만 바꾼다.
def _ensure_utf8_stdio() -> None:
    if sys.platform != "win32":
        return
    for attr in ("stdout", "stderr"):
        stream = getattr(sys, attr)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
                continue
            except Exception:
                pass
        # 구버전 대체 경로: 현재 인코딩이 이미 UTF-8 이 아닐 때만 래핑.
        if getattr(stream, "encoding", "").lower().replace("-", "") == "utf8":
            continue
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            continue
        setattr(sys, attr, io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))


_ensure_utf8_stdio()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP_ROOT = ROOT / ".tmp_e2e"
TMP_ROOT.mkdir(exist_ok=True)

VALID_STEPS = ("brief", "draft", "factcheck", "ghost")


# ---------------------------------------------------------------------------
# 결과 수집기
# ---------------------------------------------------------------------------
class StepReport:
    """한 단계(brief/draft/factcheck/ghost) 내부에서 통과/실패 체크 누적."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.checks: list[tuple[bool, str]] = []
        self.elapsed: float = 0.0
        self.usage: dict[str, int] | None = None
        self.error: str | None = None

    def ok(self, msg: str) -> None:
        self.checks.append((True, msg))

    def fail(self, msg: str) -> None:
        self.checks.append((False, msg))

    @property
    def passed(self) -> int:
        return sum(1 for ok, _ in self.checks if ok)

    @property
    def failed(self) -> int:
        return sum(1 for ok, _ in self.checks if not ok)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.error is None


def _print_step(index: int, total: int, report: StepReport, show_metrics: bool) -> None:
    print(f"[{index}/{total}] {report.title}")
    for ok, msg in report.checks:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {msg}")
    if report.error:
        print(f"  ❌ 예외: {report.error}")
    if show_metrics:
        parts = [f"{report.elapsed:.2f}s"]
        if report.usage:
            parts.append(
                f"in={report.usage.get('input_tokens', 0)} out={report.usage.get('output_tokens', 0)} tokens"
            )
        print(f"  ⏱  {' | '.join(parts)}")
    print()


# ---------------------------------------------------------------------------
# Mock 스트림 (anthropic SDK 응답 흉내)
# ---------------------------------------------------------------------------
class _FakeStreamCtx:
    """`with client.messages.stream(...) as stream:` 블록 흉내.

    - `stream.text_stream` 반복 시 `chunks` 순차 yield
    - `stream.get_final_message()` -> usage.input_tokens/output_tokens + _request_id
    """

    def __init__(self, chunks: list[str], request_id: str, input_tokens: int = 42, output_tokens: int = 128) -> None:
        self._chunks = chunks
        self._request_id = request_id
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens

    def __enter__(self) -> "_FakeStreamCtx":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    @property
    def text_stream(self):
        for chunk in self._chunks:
            yield chunk

    def get_final_message(self):
        final = SimpleNamespace()
        final.usage = SimpleNamespace(input_tokens=self._input_tokens, output_tokens=self._output_tokens)
        # anthropic SDK는 응답 객체에 `_request_id` 속성을 부여한다.
        final._request_id = self._request_id
        final.model = "mock-model"
        return final


def _fake_anthropic_factory(chunks: list[str], request_id: str) -> MagicMock:
    """`anthropic.Anthropic(...)` 호출을 가로채는 mock 팩토리 생성."""
    fake_client = MagicMock()
    fake_client.messages.stream.side_effect = lambda **kwargs: _FakeStreamCtx(chunks, request_id)
    factory = MagicMock(return_value=fake_client)
    return factory


# ---------------------------------------------------------------------------
# 공통 샘플 데이터
# ---------------------------------------------------------------------------
SAMPLE_BRIEF_JSON = {
    "working_title": "테스트 브리프: Claude 생태계 주간 동향",
    "angle": "공개 출처만으로 실무 영향을 정리한다.",
    "why_now": "배포·가격 정책 변화가 의사결정에 영향을 준다.",
    "outline": [
        {"section": "서론", "points": ["배경 정리", "왜 지금 중요한가"]},
        {"section": "본론", "points": ["핵심 변화", "실무 영향"]},
    ],
    "evidence_map": [
        {"claim": "샘플 주장", "source_id": "src-12345678"},
    ],
    "unknowns": ["최신 1차 출처 재확인 필요"],
    "risk_flags": ["E2E mock 결과이므로 실제 발행 금지"],
}

SAMPLE_DRAFT_MD = (
    "## 서론\n\n"
    "Claude 생태계의 핵심 변화를 정리한다. (src-12345678)\n\n"
    "지금 중요한 이유. (src-12345678)\n"
)

SAMPLE_FACTCHECK_MD = (
    "# 팩트체크 결과\n\n"
    "| 문장 | 판정 | 근거 |\n"
    "|---|---|---|\n"
    "| 샘플 주장 | 확인됨 | src-12345678 |\n\n"
    "## 전체 위험도\n\n"
    "낮음 — 모든 주장이 출처에 부합함.\n"
)


# ---------------------------------------------------------------------------
# 각 단계 테스트 실행기
# ---------------------------------------------------------------------------
def _apply_temp_dirs(stack: ExitStack, modules: list, attr_map: dict[str, Path]) -> None:
    """각 pipeline 모듈의 DRAFTS_DIR / LOGS_DIR 전역을 임시 경로로 교체."""
    for module in modules:
        for attr, new_path in attr_map.items():
            if hasattr(module, attr):
                stack.enter_context(patch.object(module, attr, new_path))


def run_brief_step(live: bool, tmp_drafts: Path, tmp_logs: Path) -> StepReport:
    report = StepReport("brief_generator")
    from pipeline import brief_generator

    start = time.perf_counter()
    try:
        with ExitStack() as stack:
            _apply_temp_dirs(stack, [brief_generator], {"LOGS_DIR": tmp_logs})

            brief_json_text = json.dumps(SAMPLE_BRIEF_JSON, ensure_ascii=False)
            if not live:
                factory = _fake_anthropic_factory([brief_json_text], request_id="req_brief_mock")
                stack.enter_context(patch("anthropic.Anthropic", factory))

            brief = brief_generator.generate_brief(
                topic="E2E 테스트 토픽",
                source_bundle="(E2E 테스트 소스 번들)",
                dry_run=False,
            )

        report.ok("generate_brief() 호출 성공")

        missing = brief_generator.BRIEF_REQUIRED_KEYS - set(brief.keys())
        if missing:
            report.fail(f"브리프 필수 키 누락: {sorted(missing)}")
        else:
            report.ok(f"반환 JSON 스키마 {len(brief_generator.BRIEF_REQUIRED_KEYS)}개 키 모두 존재")

        # 임시 brief.json 파일을 실제로 생성해 스키마 쓰기 가능 여부 확인 (drafts/ 대신 tmp_drafts 사용)
        brief_path = tmp_drafts / "brief_test.json"
        brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        size = brief_path.stat().st_size
        report.ok(f"{brief_path.name} 생성 확인 ({size} bytes)")

        # log 파일이 tmp_logs에 남았는지 확인
        log_files = list(tmp_logs.glob("brief_*.json"))
        if log_files:
            report.ok(f"로그 파일 생성 확인 ({log_files[0].name})")
        else:
            report.fail("brief_*.json 로그 파일이 생성되지 않음")

        report.usage = {"input_tokens": 42, "output_tokens": 128} if not live else None
    except Exception as exc:
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        report.elapsed = time.perf_counter() - start
    return report


def run_draft_step(live: bool, tmp_drafts: Path, tmp_logs: Path) -> StepReport:
    report = StepReport("draft_writer")
    from pipeline import draft_writer

    start = time.perf_counter()
    try:
        with ExitStack() as stack:
            _apply_temp_dirs(stack, [draft_writer], {"DRAFTS_DIR": tmp_drafts, "LOGS_DIR": tmp_logs})

            if not live:
                factory = _fake_anthropic_factory([SAMPLE_DRAFT_MD], request_id="req_draft_mock")
                stack.enter_context(patch("anthropic.Anthropic", factory))

            # draft_writer.write_section 은 스트리밍 청크를 stdout 으로 직접 출력하므로
            # 테스트 출력 포맷이 깨지지 않도록 /dev/null 로 리디렉트한다.
            sink = io.StringIO()
            with redirect_stdout(sink):
                intro = draft_writer.write_section(
                    SAMPLE_BRIEF_JSON, "서론", source_bundle="(테스트 소스 번들)", dry_run=False
                )
            report.ok('write_section("서론") 성공')

            with redirect_stdout(sink):
                body = draft_writer.write_section(
                    SAMPLE_BRIEF_JSON, "본론", source_bundle="(테스트 소스 번들)", dry_run=False
                )
            report.ok('write_section("본론") 성공')

        draft_path = tmp_drafts / "draft_test.md"
        draft_path.write_text(f"{intro}\n\n{body}\n", encoding="utf-8")
        size = draft_path.stat().st_size
        report.ok(f"{draft_path.name} 생성 확인 ({size} bytes)")

        log_files = list(tmp_logs.glob("draft_*.json"))
        # 참고: draft_writer 는 초단위 타임스탬프를 쓰므로 같은 초에 2회 호출되면 파일명이
        # 겹쳐 1개만 남을 수 있다. 최소 1개 이상 생성되었는지만 확인한다.
        if log_files:
            report.ok(f"draft 로그 파일 생성 확인 ({log_files[0].name})")
        else:
            report.fail("draft_*.json 로그 파일이 생성되지 않음")

        report.usage = {"input_tokens": 84, "output_tokens": 256} if not live else None
    except Exception as exc:
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        report.elapsed = time.perf_counter() - start
    return report


def run_factcheck_step(live: bool, tmp_drafts: Path, tmp_logs: Path) -> StepReport:
    report = StepReport("fact_checker")
    from pipeline import fact_checker

    start = time.perf_counter()
    try:
        with ExitStack() as stack:
            _apply_temp_dirs(stack, [fact_checker], {"LOGS_DIR": tmp_logs})

            if not live:
                factory = _fake_anthropic_factory([SAMPLE_FACTCHECK_MD], request_id="req_factcheck_mock")
                # fact_checker 모듈은 상단에서 `import anthropic` 하여 `anthropic.Anthropic` 를 호출한다.
                stack.enter_context(patch.object(fact_checker.anthropic, "Anthropic", factory))

            # fact_checker.run_factcheck 도 스트리밍 청크를 stdout 에 직접 출력한다.
            sink = io.StringIO()
            with redirect_stdout(sink):
                result = fact_checker.run_factcheck(
                    draft_text=SAMPLE_DRAFT_MD,
                    source_bundle="[src-12345678] TestPub — https://example.com/article",
                )

        report.ok("run_factcheck() 성공")

        log_files = list(tmp_logs.glob("factcheck_*.json"))
        if log_files:
            try:
                payload = json.loads(log_files[0].read_text(encoding="utf-8"))
                if payload.get("request_id"):
                    report.ok(f"{log_files[0].name} 생성 (request_id 포함)")
                else:
                    report.fail(f"{log_files[0].name} 생성되었지만 request_id 누락")
            except Exception as exc:
                report.fail(f"로그 JSON 파싱 실패: {exc}")
        else:
            report.fail("factcheck_*.json 로그 파일이 생성되지 않음")

        if "전체 위험도" in result:
            report.ok('출력에 "전체 위험도" 섹션 포함')
        else:
            report.fail('출력에 "전체 위험도" 섹션이 없음')

        report.usage = {"input_tokens": 256, "output_tokens": 512} if not live else None
    except Exception as exc:
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        report.elapsed = time.perf_counter() - start
    return report


def run_ghost_step(live: bool) -> StepReport:
    report = StepReport("ghost_client")
    from pipeline import ghost_client

    start = time.perf_counter()
    try:
        with ExitStack() as stack:
            if not live:
                # Ghost env 가 없으면 JWT 생성이 불가하므로 mock 값 주입.
                # Ghost Admin API Key 형식: "kid:hex_secret" (secret 은 짝수 길이 16진수)
                stack.enter_context(patch.dict(os.environ, {
                    "GHOST_ADMIN_API_URL": os.environ.get("GHOST_ADMIN_API_URL", "https://example.ghost.io"),
                    "GHOST_ADMIN_API_KEY": os.environ.get(
                        "GHOST_ADMIN_API_KEY",
                        # kid:hex_secret 포맷. secret 은 32 bytes (64 hex) 로 RFC 7518 권장 길이 충족.
                        "test-kid:" + ("ab" * 32),
                    ),
                }, clear=False))

                # JWT 토큰 생성 경로는 실제로 실행한다 (키 포맷 검증).
                token = ghost_client._get_token()
                if token and token.count(".") == 2:
                    report.ok(f"JWT 토큰 생성 성공 (len={len(token)})")
                else:
                    report.fail("JWT 토큰 형식이 JWS (header.payload.sig) 가 아님")

                fake_response = MagicMock()
                fake_response.raise_for_status.return_value = None
                fake_response.json.return_value = {
                    "posts": [
                        {
                            "id": "mock_post_id_123",
                            "url": "https://example.ghost.io/p/mock-post/",
                            "status": "draft",
                        }
                    ]
                }
                # 실제 코드는 `requests.request(method="POST", ...)` 를 호출한다.
                # TASK 명세의 "requests.post patch" 는 HTTP 레이어 치환을 의미하므로
                # `requests.request` 를 치환해 동등하게 가로챈다.
                stack.enter_context(
                    patch.object(ghost_client.requests, "request", return_value=fake_response)
                )
            else:
                # live 모드에서는 실제 요청이 나가므로 token 만 만들어서 형식 체크.
                token = ghost_client._get_token()
                if token and token.count(".") == 2:
                    report.ok(f"JWT 토큰 생성 성공 (len={len(token)})")
                else:
                    report.fail("JWT 토큰 형식이 JWS 가 아님")

            result = ghost_client.create_post(
                title="E2E 스모크 테스트 (mock)",
                html="<p>E2E 스모크 테스트 본문.</p>",
                status="draft",
            )

        if not isinstance(result, dict):
            report.fail(f"create_post() 반환 타입 오류: {type(result).__name__}")
        else:
            report.ok("create_post() 응답 파싱 성공")
            missing = {"post_id", "url", "status"} - set(result.keys())
            if missing:
                report.fail(f"반환값에 누락 키: {sorted(missing)}")
            else:
                report.ok("반환값에 post_id, url, status 모두 포함")
    except Exception as exc:
        report.error = f"{type(exc).__name__}: {exc}"
    finally:
        report.elapsed = time.perf_counter() - start
    return report


# ---------------------------------------------------------------------------
# 오케스트레이터
# ---------------------------------------------------------------------------
STEP_RUNNERS: dict[str, str] = {
    "brief": "run_brief_step",
    "draft": "run_draft_step",
    "factcheck": "run_factcheck_step",
    "ghost": "run_ghost_step",
}


def _require_anthropic_key_for_mock() -> None:
    """Mock 모드에서도 pipeline 코드가 `os.environ["ANTHROPIC_API_KEY"]` 를 참조하므로 주입."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-dummy")


def _preload_pipeline_modules() -> None:
    """
    파이프라인 모듈을 선행 import.
    특히 fact_checker 는 import 시점에 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`
    로 스트림 객체를 교체한다. 이 import 가 테스트 본문 print 후에 일어나면 원본 stdout
    래퍼가 GC 되면서 공유 버퍼가 닫혀 후속 출력이 사라진다.
    따라서 모든 단계가 시작되기 전에 eager import 하여 stdio 교체를 일괄 처리한다.
    """
    import pipeline.brief_generator  # noqa: F401
    import pipeline.draft_writer  # noqa: F401
    import pipeline.fact_checker  # noqa: F401
    import pipeline.ghost_client  # noqa: F401


def _run_check_env_strict() -> int:
    """--live 선행: check_env.py --strict 서브프로세스 호출."""
    print(">>> --live 모드: scripts/check_env.py --strict 선행 호출")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_env.py"), "--strict"],
        cwd=str(ROOT),
    )
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Magazine E2E 스모크 테스트")
    parser.add_argument(
        "--step",
        choices=VALID_STEPS,
        help="특정 단계만 실행 (brief|draft|factcheck|ghost)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="실제 API 호출 (ANTHROPIC/Ghost 환경변수 필요, 비용 발생)",
    )
    args = parser.parse_args()

    if args.live:
        rc = _run_check_env_strict()
        if rc != 0:
            print(f"❌ check_env --strict 실패 (exit {rc}) — --live 실행 중단", file=sys.stderr)
            return 1
        mode_label = "live 모드"
    else:
        _require_anthropic_key_for_mock()
        mode_label = "mock 모드"

    # 모든 pipeline 모듈을 선행 import 해 stdio 교체를 한 번에 처리한다.
    _preload_pipeline_modules()

    selected = [args.step] if args.step else list(VALID_STEPS)

    print(f"=== E2E 스모크 테스트 ({mode_label}) ===\n")

    reports: list[StepReport] = []
    tmp_drafts = TMP_ROOT / f"e2e_drafts_{uuid.uuid4().hex[:8]}"
    tmp_logs = TMP_ROOT / f"e2e_logs_{uuid.uuid4().hex[:8]}"
    tmp_drafts.mkdir(parents=True, exist_ok=True)
    tmp_logs.mkdir(parents=True, exist_ok=True)
    try:
        total = len(selected)
        for idx, step in enumerate(selected, start=1):
            runner_name = STEP_RUNNERS[step]
            runner = globals()[runner_name]
            if step == "ghost":
                report = runner(args.live)
            else:
                report = runner(args.live, tmp_drafts, tmp_logs)
            reports.append(report)
            _print_step(idx, total, report, show_metrics=args.live)
    finally:
        shutil.rmtree(tmp_drafts, ignore_errors=True)
        shutil.rmtree(tmp_logs, ignore_errors=True)

    total_passed = sum(r.passed for r in reports)
    total_failed = sum(r.failed for r in reports) + sum(1 for r in reports if r.error)
    any_failed = any(not r.all_passed for r in reports)

    verdict = "전체 흐름 정상" if not any_failed else "실패 포함 — 로그 확인 필요"
    print(f"=== 결과: {total_passed} 통과 / {total_failed} 실패 — {verdict} ===")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
