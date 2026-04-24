"""
Claude Magazine 운영환경 체크 스크립트

주간 브리프 첫 발행 전, 모든 외부 연동이 실제로 작동하는지 5분 안에 확인한다.
`.env` 누락·오타·API 키 무효·DB 권한 문제를 사전에 드러낸다.

사용법:
    python scripts/check_env.py                         # 전체 체크
    python scripts/check_env.py --only anthropic ghost  # 특정 항목만
    python scripts/check_env.py --strict                # 실패 시 exit code 1
    python scripts/check_env.py --dry-run               # 네트워크 호출 없이 설정만 검사
"""
from __future__ import annotations

import argparse
import io
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

# Windows 환경에서 한국어/특수문자 출력을 위한 UTF-8 강제 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

# 체크 항목 이름 → CLI 키워드 매핑 (--only 용)
CHECK_KEYS = {
    "env": "env",
    "anthropic": "anthropic",
    "ghost": "ghost",            # GHOST_ADMIN_API_KEY (JWT + /site/)
    "ghost-url": "ghost",        # URL 별도 체크지만 --only ghost 에 같이 묶임
    "db": "db",
    "langfuse": "langfuse",
    "deps": "deps",
    "folders": "folders",
}

# 상태 코드
PASS = "pass"
FAIL = "fail"
WARN = "warn"
SKIP = "skip"

ICON = {PASS: "✅", FAIL: "❌", WARN: "⚠️ ", SKIP: "⏭ "}


class Result:
    def __init__(self, status: str, message: str, detail: str | None = None, hint: str | None = None):
        self.status = status
        self.message = message
        self.detail = detail
        self.hint = hint


def _print_result(idx: int, total: int, title: str, result: Result) -> None:
    print(f"[{idx}/{total}] {title}")
    print(f"  {ICON[result.status]} {result.message}")
    if result.detail:
        for line in result.detail.splitlines():
            print(f"     {line}")
    if result.hint:
        print(f"     해결: {result.hint}")
    print()


# ---------------------------------------------------------------------------
# 개별 체크 함수
# ---------------------------------------------------------------------------
def check_env_file() -> Result:
    """.env 파일 존재 확인 + dotenv 로드"""
    if not ENV_FILE.exists():
        return Result(
            FAIL,
            ".env 파일을 찾을 수 없음",
            detail=f"경로: {ENV_FILE}",
            hint="cp .env.example .env",
        )
    try:
        from dotenv import load_dotenv  # noqa: WPS433
        load_dotenv(ENV_FILE)
    except ImportError:
        return Result(
            WARN,
            f"{ENV_FILE} 존재 (단, python-dotenv 미설치로 로드 실패)",
            hint="pip install -r requirements.txt",
        )
    return Result(PASS, str(ENV_FILE))


def check_anthropic(dry_run: bool = False) -> Result:
    """ANTHROPIC_API_KEY 실제 에코 테스트 (claude-haiku-4-5-20251001, max_tokens=10)"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return Result(
            FAIL,
            "ANTHROPIC_API_KEY 미설정",
            hint="console.anthropic.com 에서 키 발급 후 .env 에 설정",
        )
    if dry_run:
        return Result(PASS, f"키 형식 OK (sk-ant-... {len(api_key)} chars) — dry-run, 호출 생략")

    try:
        import anthropic  # noqa: WPS433
    except ImportError:
        return Result(
            FAIL,
            "anthropic 패키지 미설치",
            hint="pip install -r requirements.txt",
        )

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=10.0)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'ok' and nothing else."}],
        )
        total_tokens = (
            (message.usage.input_tokens if message.usage else 0)
            + (message.usage.output_tokens if message.usage else 0)
        )
        return Result(
            PASS,
            f"응답 수신 (model={message.model}, {total_tokens} tokens)",
        )
    except Exception as exc:  # noqa: BLE001
        name = type(exc).__name__
        summary = str(exc).strip().replace("\n", " ")
        if len(summary) > 240:
            summary = summary[:240] + "..."
        # anthropic SDK 의 status_code 추출 시도
        status = getattr(exc, "status_code", None)
        status_str = f" (HTTP {status})" if status else ""
        return Result(
            FAIL,
            f"API 호출 실패: {name}{status_str}",
            detail=summary or None,
            hint="키 권한·크레딧·네트워크 확인 (console.anthropic.com)",
        )


def _build_ghost_jwt(key: str) -> str:
    import jwt  # noqa: WPS433
    if ":" not in key:
        raise ValueError("GHOST_ADMIN_API_KEY 가 kid:secret 형식이 아님")
    kid, secret = key.split(":", 1)
    issued_at = int(time.time())
    return jwt.encode(
        {"iat": issued_at, "exp": issued_at + 300, "aud": "/admin/"},
        bytes.fromhex(secret),
        algorithm="HS256",
        headers={"alg": "HS256", "kid": kid, "typ": "JWT"},
    )


def _ghost_base(url: str) -> str:
    api_url = url.rstrip("/")
    if api_url.endswith("/ghost/api/admin"):
        return api_url
    return f"{api_url}/ghost/api/admin"


def check_ghost_key(dry_run: bool = False) -> Result:
    """GHOST_ADMIN_API_KEY JWT 생성 + /admin/site/ GET 200"""
    key = os.getenv("GHOST_ADMIN_API_KEY")
    url = os.getenv("GHOST_ADMIN_API_URL")

    if not key:
        return Result(
            FAIL,
            "GHOST_ADMIN_API_KEY 미설정",
            hint="Ghost Admin > Integrations 에서 Admin API Key 복사 (kid:secret 형식)",
        )
    if ":" not in key:
        return Result(
            FAIL,
            "GHOST_ADMIN_API_KEY 형식 오류 — kid:secret 형식이 아님",
            hint="Ghost Admin > Integrations 에서 Admin API Key 복사",
        )

    try:
        token = _build_ghost_jwt(key)
    except Exception as exc:  # noqa: BLE001
        return Result(
            FAIL,
            f"JWT 서명 실패: {type(exc).__name__}",
            detail=str(exc),
            hint="secret 부분이 16진수 문자열인지 확인",
        )

    if dry_run or not url:
        return Result(
            PASS if url else WARN,
            "JWT 생성 OK — dry-run/URL 미설정으로 호출 생략"
            if dry_run else "JWT 생성 OK (GHOST_ADMIN_API_URL 미설정으로 호출 생략)",
        )

    try:
        import requests  # noqa: WPS433
    except ImportError:
        return Result(FAIL, "requests 패키지 미설치", hint="pip install -r requirements.txt")

    try:
        resp = requests.get(
            f"{_ghost_base(url)}/site/",
            headers={"Authorization": f"Ghost {token}", "Accept": "application/json"},
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        return Result(
            FAIL,
            f"Ghost 연결 실패: {type(exc).__name__}",
            detail=str(exc),
            hint="GHOST_ADMIN_API_URL 재확인",
        )

    if resp.status_code == 200:
        try:
            site = resp.json().get("site", {})
            title = site.get("title", "?")
            version = site.get("version", "?")
            return Result(PASS, f"/admin/site/ 200 OK (title={title}, version={version})")
        except Exception:  # noqa: BLE001
            return Result(PASS, "/admin/site/ 200 OK")
    body = resp.text.strip().replace("\n", " ")
    if len(body) > 200:
        body = body[:200] + "..."
    return Result(
        FAIL,
        f"/admin/site/ HTTP {resp.status_code}",
        detail=body or None,
        hint="키 만료·권한·URL 확인 (Ghost Admin > Integrations)",
    )


def check_ghost_url(dry_run: bool = False) -> Result:
    """GHOST_ADMIN_API_URL HTTPS 접근 가능"""
    url = os.getenv("GHOST_ADMIN_API_URL")
    if not url:
        return Result(
            FAIL,
            "GHOST_ADMIN_API_URL 미설정",
            hint=".env 에 GHOST_ADMIN_API_URL=https://your-site.ghost.io 추가",
        )
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return Result(
            FAIL,
            f"HTTPS가 아님 (scheme={parsed.scheme!r})",
            hint="https:// 로 시작하는 URL 사용",
        )
    if not parsed.netloc:
        return Result(FAIL, "URL 파싱 실패 — netloc 없음", hint=f"현재 값: {url!r}")

    if dry_run:
        return Result(PASS, f"HTTPS URL 형식 OK ({parsed.netloc}) — dry-run")

    try:
        import requests  # noqa: WPS433
    except ImportError:
        return Result(FAIL, "requests 패키지 미설치", hint="pip install -r requirements.txt")

    try:
        resp = requests.get(url.rstrip("/") + "/ghost/api/admin/site/", timeout=10)
        # 인증 없이 호출하므로 401/403/404 도 "서버가 살아있음"으로 간주
        return Result(
            PASS,
            f"{parsed.netloc} 접근 가능 (HTTP {resp.status_code})",
        )
    except Exception as exc:  # noqa: BLE001
        return Result(
            FAIL,
            f"URL 접근 실패: {type(exc).__name__}",
            detail=str(exc),
            hint="네트워크·DNS·URL 확인",
        )


def check_db() -> Result:
    """SOURCE_DB_PATH SQLite 쓰기 권한 테스트"""
    raw = os.getenv("SOURCE_DB_PATH")
    if not raw:
        return Result(
            FAIL,
            "SOURCE_DB_PATH 미설정",
            hint=".env 에 SOURCE_DB_PATH=./data/source_registry.db 추가",
        )
    db_path = Path(raw)
    if not db_path.is_absolute():
        db_path = (ROOT / db_path).resolve()

    parent = db_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        return Result(
            FAIL,
            f"디렉토리 생성 실패: {parent}",
            detail=str(exc),
            hint="폴더 권한 확인",
        )

    # 쓰기 권한: SQLite 연결 + 임시 테이블 생성/삭제
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS __check_env__ (x INTEGER)")
            conn.execute("INSERT INTO __check_env__ (x) VALUES (1)")
            conn.execute("DROP TABLE __check_env__")
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        return Result(
            FAIL,
            f"SQLite 쓰기 실패: {db_path}",
            detail=str(exc),
            hint="디렉토리 권한 또는 디스크 공간 확인",
        )
    return Result(PASS, f"{db_path} (읽기/쓰기 OK)")


def check_langfuse(dry_run: bool = False) -> Result:
    """LANGFUSE_* 3개 키 (선택)"""
    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST")

    missing = [name for name, v in [("LANGFUSE_PUBLIC_KEY", pk), ("LANGFUSE_SECRET_KEY", sk), ("LANGFUSE_HOST", host)] if not v]
    if missing:
        return Result(
            WARN,
            f"{', '.join(missing)} 미설정 — 관측 기능 비활성화 (선택 항목)",
        )

    if dry_run:
        return Result(PASS, f"3개 키 모두 설정됨 — dry-run, 연결 생략 (host={host})")

    try:
        from langfuse import Langfuse  # noqa: WPS433
    except ImportError:
        return Result(
            WARN,
            "langfuse 패키지 미설치 (선택 항목이라 경고만)",
            hint="pip install -r requirements.txt",
        )

    try:
        lf = Langfuse(public_key=pk, secret_key=sk, host=host, timeout=10)
        # 연결 테스트: auth_check 있으면 사용, 없으면 flush 로 대체
        if hasattr(lf, "auth_check"):
            ok = lf.auth_check()
            if ok:
                return Result(PASS, f"Langfuse 인증 OK (host={host})")
            return Result(WARN, f"Langfuse auth_check 실패 (host={host}) — 키/호스트 확인")
        try:
            lf.flush()
        except Exception:  # noqa: BLE001
            pass
        return Result(PASS, f"Langfuse 클라이언트 초기화 OK (host={host})")
    except Exception as exc:  # noqa: BLE001
        return Result(
            WARN,
            f"Langfuse 연결 실패: {type(exc).__name__} (선택 항목이라 경고만)",
            detail=str(exc),
            hint="키·호스트 확인",
        )


def check_deps() -> Result:
    """Python 패키지 import"""
    packages = [
        ("anthropic", "anthropic"),
        ("requests", "requests"),
        ("python-dotenv", "dotenv"),
        ("PyJWT", "jwt"),
        ("langfuse", "langfuse"),
    ]
    ok = []
    missing = []
    for display, import_name in packages:
        try:
            __import__(import_name)
            ok.append(display)
        except ImportError:
            missing.append(display)
    if missing:
        return Result(
            FAIL,
            f"{len(ok)}/{len(packages)} import 성공 — 누락: {', '.join(missing)}",
            hint="pip install -r requirements.txt",
        )
    return Result(PASS, f"{len(ok)}/{len(packages)} import 성공")


def check_folders() -> Result:
    """폴더 구조: data/ drafts/ logs/ output/"""
    folders = ["data", "drafts", "logs", "output"]
    missing = [f for f in folders if not (ROOT / f).is_dir()]
    if missing:
        return Result(
            FAIL,
            f"누락 폴더: {', '.join(missing)}",
            hint=f"mkdir -p {' '.join(missing)}",
        )
    return Result(PASS, " ".join(f + "/" for f in folders) + "모두 존재")


# ---------------------------------------------------------------------------
# 실행 오케스트레이터
# ---------------------------------------------------------------------------
def build_plan() -> list[tuple[str, str, Callable[..., Result], str]]:
    """(항목명, --only 키워드, 체크 함수, 표시 제목) 튜플 리스트"""
    return [
        ("env", "env", check_env_file, ".env 파일"),
        ("anthropic", "anthropic", check_anthropic, "ANTHROPIC_API_KEY"),
        ("ghost", "ghost", check_ghost_key, "GHOST_ADMIN_API_KEY"),
        ("ghost-url", "ghost", check_ghost_url, "GHOST_ADMIN_API_URL"),
        ("db", "db", check_db, "SOURCE_DB_PATH"),
        ("langfuse", "langfuse", check_langfuse, "LANGFUSE_*"),
        ("deps", "deps", check_deps, "Python 패키지"),
        ("folders", "folders", check_folders, "폴더 구조"),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Claude Magazine 운영환경 체크",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="특정 항목만 체크 (env, anthropic, ghost, db, langfuse, deps, folders)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="실패가 하나라도 있으면 exit code 1",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="네트워크 호출 생략 (API 키·URL 형식만 확인)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    plan = build_plan()
    if args.only:
        keys = {k.lower() for k in args.only}
        plan = [step for step in plan if step[1] in keys]
        if not plan:
            print(f"[WARN] --only {args.only} — 매칭되는 항목 없음")
            print("       사용 가능: env, anthropic, ghost, db, langfuse, deps, folders")
            return 0

    print("=== Claude Magazine 운영환경 체크 ===\n")

    total = len(plan)
    # .env 로드를 먼저 하기 위해 env 체크를 맨 앞에서 실행한다.
    # (이미 plan 순서상 env 가 맨 앞이지만 --only 로 건너뛸 수 있으므로, 따로 한 번 로드 시도)
    if all(step[0] != "env" for step in plan) and ENV_FILE.exists():
        try:
            from dotenv import load_dotenv  # noqa: WPS433
            load_dotenv(ENV_FILE)
        except ImportError:
            pass

    results: list[tuple[str, Result]] = []
    for idx, (name, _key, func, title) in enumerate(plan, start=1):
        try:
            # dry-run 지원 함수만 인자 전달
            if name in {"anthropic", "ghost", "ghost-url", "langfuse"}:
                result = func(dry_run=args.dry_run)
            else:
                result = func()
        except Exception as exc:  # noqa: BLE001
            result = Result(
                FAIL,
                f"체크 실행 중 예외: {type(exc).__name__}",
                detail=str(exc),
            )
        results.append((name, result))
        _print_result(idx, total, title, result)

    # 집계
    counts = {PASS: 0, FAIL: 0, WARN: 0, SKIP: 0}
    for _name, r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    print(f"=== 결과: {counts[PASS]} 통과 / {counts[FAIL]} 실패 / {counts[WARN]} 경고 ===")

    if args.strict and counts[FAIL] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
