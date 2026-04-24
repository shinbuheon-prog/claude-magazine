"""
Claude Magazine — n8n 워크플로우 import 자동화 (TASK_014)

`n8n/` 폴더의 3개 워크플로우 JSON 을 n8n REST API 로 일괄 import/update 한다.
수동 UI 클릭 의존성을 제거해 재배포·롤백을 빠르게 한다.

사용법:
    python scripts/n8n_import.py                                  # 전체 import (기존 존재 시 스킵)
    python scripts/n8n_import.py --workflow workflow_1_scheduler.json
    python scripts/n8n_import.py --overwrite                      # 이름 일치 시 PUT 으로 덮어쓰기
    python scripts/n8n_import.py --dry-run                        # 실제 API 호출 없이 요청 본문만 미리보기

환경변수 (.env):
    N8N_BASE_URL   예: https://your-n8n-instance.n8n.cloud
    N8N_API_KEY    예: n8n_api_xxx... (Settings → API 에서 발급)

REST 엔드포인트 (n8n public REST API):
    GET    /rest/workflows
    POST   /rest/workflows
    PUT    /rest/workflows/:id
    GET    /rest/workflows/:id

인증 헤더: X-N8N-API-KEY: {N8N_API_KEY}
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Windows 환경에서 한국어/특수문자 출력 깨짐 방지
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
N8N_DIR = ROOT / "n8n"

HTTP_TIMEOUT = 15           # 초
MAX_RETRIES = 3             # 네트워크 실패 시 재시도 횟수
RETRY_INTERVAL = 15         # 재시도 간격 (초)

# 워크플로우 생성/업데이트 시 n8n REST API 가 허용하는 키 화이트리스트.
# (id/createdAt/updatedAt 같은 서버 관리 필드는 제거해야 한다.)
ALLOWED_PAYLOAD_KEYS = {
    "name",
    "nodes",
    "connections",
    "settings",
    "staticData",
    "pinData",
    "tags",
    "active",
}


# ---------------------------------------------------------------------------
# 환경설정 / .env
# ---------------------------------------------------------------------------
def load_env() -> None:
    """.env 파일을 로드한다. (없어도 OS env 에 이미 있으면 그대로 진행)"""
    try:
        from dotenv import load_dotenv  # noqa: WPS433
    except ImportError:
        print("[WARN] python-dotenv 미설치 — .env 로드 생략 (pip install -r requirements.txt)")
        return
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"[ERROR] 환경변수 {name} 가 설정되지 않았습니다.")
        print(f"        .env 파일 또는 쉘 환경에 {name} 을 설정한 뒤 재실행하세요.")
        print(f"        예: {name}=...")
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# n8n REST API 래퍼
# ---------------------------------------------------------------------------
class N8nClient:
    def __init__(self, base_url: str, api_key: str, *, dry_run: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dry_run = dry_run

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-N8N-API-KEY": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def _request_with_retry(self, method: str, path: str, *, json_body: Any = None):
        """requests.request 호출 + 최대 MAX_RETRIES 회 재시도.

        - ConnectionError/Timeout → 재시도
        - 그 외 HTTP 응답(401, 403, 5xx 등) → 즉시 반환 (재시도 안 함)
        """
        import requests  # lazy import

        url = self._url(path)
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    json=json_body,
                    timeout=HTTP_TIMEOUT,
                )
                return resp
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    print(
                        f"     ⚠️  네트워크 오류 ({type(exc).__name__}) — "
                        f"{RETRY_INTERVAL}s 후 재시도 ({attempt}/{MAX_RETRIES})"
                    )
                    time.sleep(RETRY_INTERVAL)
                else:
                    print(
                        f"     ❌ 네트워크 오류 — {MAX_RETRIES}회 재시도 실패 "
                        f"({type(exc).__name__})"
                    )
        if last_exc:
            raise last_exc
        raise RuntimeError("unreachable")

    # --- 공개 메서드 ------------------------------------------------------
    def list_workflows(self) -> list[dict[str, Any]]:
        """GET /rest/workflows → 전체 목록."""
        resp = self._request_with_retry("GET", "/rest/workflows")
        _raise_for_auth(resp)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"GET /rest/workflows 실패 (HTTP {resp.status_code}): {_safe_body(resp)}"
            )
        data = resp.json()
        # n8n 응답 포맷: {"data": [...]} 또는 바로 배열
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        raise RuntimeError(f"예상치 못한 응답 형식: {type(data).__name__}")

    def create_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /rest/workflows → 신규 생성."""
        if self.dry_run:
            print("     [dry-run] POST /rest/workflows")
            _print_payload_preview(payload)
            return {"id": "dry-run", "name": payload.get("name")}
        resp = self._request_with_retry("POST", "/rest/workflows", json_body=payload)
        _raise_for_auth(resp)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"POST /rest/workflows 실패 (HTTP {resp.status_code}): {_safe_body(resp)}"
            )
        data = resp.json()
        return data.get("data", data)

    def update_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """PUT /rest/workflows/:id → 업데이트."""
        path = f"/rest/workflows/{workflow_id}"
        if self.dry_run:
            print(f"     [dry-run] PUT {path}")
            _print_payload_preview(payload)
            return {"id": workflow_id, "name": payload.get("name")}
        resp = self._request_with_retry("PUT", path, json_body=payload)
        _raise_for_auth(resp)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"PUT {path} 실패 (HTTP {resp.status_code}): {_safe_body(resp)}"
            )
        data = resp.json()
        return data.get("data", data)


def _raise_for_auth(resp) -> None:
    """401/403 응답 시 즉시 안내 후 종료."""
    if resp.status_code in (401, 403):
        print(f"     ❌ HTTP {resp.status_code} — 인증 실패")
        print("        API 키 확인 필요: N8N_API_KEY 가 만료되었거나 권한이 부족합니다.")
        print(f"        응답: {_safe_body(resp)}")
        sys.exit(1)


def _safe_body(resp) -> str:
    try:
        body = resp.text.strip().replace("\n", " ")
    except Exception:  # noqa: BLE001
        return "<응답 본문 읽기 실패>"
    if len(body) > 300:
        body = body[:300] + "..."
    return body or "<빈 본문>"


def _print_payload_preview(payload: dict[str, Any]) -> None:
    """드라이런 때 요청 본문의 핵심 구조만 요약 출력한다."""
    name = payload.get("name")
    n_nodes = len(payload.get("nodes") or [])
    conn_keys = list((payload.get("connections") or {}).keys())
    tags = payload.get("tags", [])
    active = payload.get("active")
    settings_keys = list((payload.get("settings") or {}).keys())
    print(f"     └─ name     : {name}")
    print(f"     └─ nodes    : {n_nodes} 개")
    print(f"     └─ connections: {len(conn_keys)} 노드 연결 "
          f"({', '.join(conn_keys[:3])}{'...' if len(conn_keys) > 3 else ''})")
    print(f"     └─ settings : {settings_keys if settings_keys else '(none)'}")
    print(f"     └─ tags     : {tags if tags else '(none)'}")
    print(f"     └─ active   : {active}")


# ---------------------------------------------------------------------------
# 워크플로우 파일 / payload 처리
# ---------------------------------------------------------------------------
def sanitize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """n8n REST API POST/PUT 이 받지 않는 서버 관리 필드를 제거한다."""
    payload = {k: v for k, v in raw.items() if k in ALLOWED_PAYLOAD_KEYS}
    # n8n 은 nodes/connections 필수. 없으면 빈 값으로 채운다.
    payload.setdefault("nodes", raw.get("nodes", []))
    payload.setdefault("connections", raw.get("connections", {}))
    # settings 는 생성 시 없으면 빈 객체.
    payload.setdefault("settings", raw.get("settings", {}))
    return payload


def discover_workflow_files(filter_name: str | None) -> list[Path]:
    """n8n/workflow_*.json 파일 탐색. filter_name 이 있으면 해당 파일만 반환."""
    if not N8N_DIR.is_dir():
        print(f"[ERROR] n8n 디렉토리를 찾을 수 없습니다: {N8N_DIR}")
        sys.exit(1)

    if filter_name:
        target = N8N_DIR / filter_name
        if not target.exists():
            print(f"[ERROR] 지정한 워크플로우 파일이 없습니다: {target}")
            sys.exit(1)
        return [target]

    files = sorted(N8N_DIR.glob("workflow_*.json"))
    if not files:
        print(f"[ERROR] n8n/workflow_*.json 파일을 찾을 수 없습니다: {N8N_DIR}")
        sys.exit(1)
    return files


def load_workflow_json(path: Path) -> dict[str, Any] | None:
    """단일 워크플로우 JSON 로드. 파싱 실패 시 None 반환 (상위에서 다음 파일로 진행)."""
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  ❌ JSON 파싱 실패: {path.name} — {exc}")
        return None
    except OSError as exc:
        print(f"  ❌ 파일 읽기 실패: {path.name} — {exc}")
        return None

    if not isinstance(data, dict) or not data.get("name"):
        print(f"  ❌ 유효하지 않은 워크플로우 JSON (name 필드 없음): {path.name}")
        return None
    return data


# ---------------------------------------------------------------------------
# 메인 import 로직
# ---------------------------------------------------------------------------
def import_workflows(
    client: N8nClient,
    files: list[Path],
    *,
    overwrite: bool,
) -> tuple[int, int, int]:
    """return (success, fail, skip)"""
    # 1) 기존 워크플로우 이름 → id 매핑
    #    dry-run 모드에서는 실제 API 호출을 전혀 하지 않고 "전부 신규" 로 간주한다.
    existing: list[dict[str, Any]] = []
    if client.dry_run:
        print("\n[dry-run] GET /rest/workflows 호출 생략 — 모든 파일을 신규로 표시합니다.")
    else:
        try:
            existing = client.list_workflows()
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] 기존 워크플로우 목록 조회 실패: {exc}")
            sys.exit(1)

    name_to_id: dict[str, str] = {}
    for wf in existing:
        wf_name = wf.get("name")
        wf_id = wf.get("id")
        if wf_name and wf_id is not None:
            name_to_id[wf_name] = str(wf_id)

    success = fail = skip = 0
    total = len(files)

    for idx, path in enumerate(files, start=1):
        print(f"\n[{idx}/{total}] {path.name}")
        raw = load_workflow_json(path)
        if raw is None:
            fail += 1
            continue

        payload = sanitize_payload(raw)
        wf_name = payload.get("name", "(이름 없음)")
        existing_id = name_to_id.get(wf_name)

        try:
            if existing_id is not None:
                print(f"  ℹ️  기존 워크플로우 발견 (id: {existing_id}, 이름: \"{wf_name}\")")
                if not overwrite:
                    print("  ⏭  스킵 — 이미 존재함 (--overwrite 없음)")
                    skip += 1
                    continue
                result = client.update_workflow(existing_id, payload)
                new_id = result.get("id", existing_id)
                print(f"  ✅ PUT 성공 — 업데이트됨 (id: {new_id})")
                success += 1
            else:
                print(f"  ℹ️  신규 워크플로우 (이름: \"{wf_name}\")")
                result = client.create_workflow(payload)
                new_id = result.get("id", "?")
                print(f"  ✅ POST 성공 — 신규 생성 (id: {new_id})")
                success += 1
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ 실패 ({type(exc).__name__}): {exc}")
            fail += 1

    return success, fail, skip


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="n8n 워크플로우 JSON 을 n8n REST API 로 import/update",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            "  python scripts/n8n_import.py\n"
            "  python scripts/n8n_import.py --workflow workflow_1_scheduler.json\n"
            "  python scripts/n8n_import.py --overwrite\n"
            "  python scripts/n8n_import.py --dry-run\n"
        ),
    )
    parser.add_argument(
        "--workflow",
        metavar="FILENAME",
        help="n8n/ 폴더 내 특정 파일만 import (예: workflow_1_scheduler.json)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="이름이 일치하는 기존 워크플로우를 PUT 으로 덮어쓴다 (기본은 스킵)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 API 호출 없이 요청 URL/본문 구조만 미리보기",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()

    # 드라이런이라도 환경변수는 기본 요구한다 (실제 운영 설정 누락 조기 감지).
    base_url = require_env("N8N_BASE_URL")
    api_key = require_env("N8N_API_KEY")

    # requests 패키지 필수
    try:
        import requests  # noqa: F401, WPS433
    except ImportError:
        print("[ERROR] requests 패키지 미설치 — pip install -r requirements.txt")
        return 1

    files = discover_workflow_files(args.workflow)

    print("=== n8n 워크플로우 Import ===")
    print(f"대상 파일 : {len(files)} 개")
    print(f"n8n 주소  : {base_url}")
    print(f"dry-run   : {args.dry_run}")
    print(f"overwrite : {args.overwrite}")

    client = N8nClient(base_url, api_key, dry_run=args.dry_run)
    success, fail, skip = import_workflows(client, files, overwrite=args.overwrite)

    print(f"\n=== 결과: {success} 성공 / {fail} 실패 / {skip} 스킵 ===")
    if success > 0 and not args.dry_run:
        print("\n활성화하려면:")
        print("  n8n UI 에서 각 워크플로우의 \"Active\" 토글 ON")

    return 0 if fail == 0 else 1


# ---------------------------------------------------------------------------
# 스모크 테스트 (python scripts/n8n_import.py --dry-run)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
