"""
Ghost Webhook 자동 등록 유틸리티.

Ghost CMS의 `post.published` 이벤트를 n8n workflow_3_sns Webhook으로 등록한다.
JWT 생성 로직은 `pipeline.ghost_client._get_token` 을 재사용한다 (중복 구현 금지).

CLI
---
    python pipeline/ghost_webhook_setup.py --register
    python pipeline/ghost_webhook_setup.py --register --dry-run
    python pipeline/ghost_webhook_setup.py --list
    python pipeline/ghost_webhook_setup.py --delete <WEBHOOK_ID>
    python pipeline/ghost_webhook_setup.py --register --overwrite
    python pipeline/ghost_webhook_setup.py --register --event page.published
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv

# JWT 인증은 ghost_client._get_token 을 재사용한다 (중복 구현 금지).
# 스크립트로 직접 실행되는 경우(`python pipeline/ghost_webhook_setup.py`)에도
# 동작하도록 두 가지 import 경로를 모두 지원한다.
try:
    from pipeline.ghost_client import _admin_api_base, _get_token
except ModuleNotFoundError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from pipeline.ghost_client import _admin_api_base, _get_token  # noqa: E402

load_dotenv()

# Windows 콘솔 UTF-8 출력 깨짐 방지
if sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

DEFAULT_NAME = "Claude Magazine — SNS Rewriter"
DEFAULT_EVENT = "post.published"
DEFAULT_WEBHOOK_PATH = "/webhook/ghost-post-published"
HTTP_TIMEOUT = 10


# --------------------------------------------------------------------------- #
# 내부 유틸
# --------------------------------------------------------------------------- #
def _headers() -> dict[str, str]:
    """Ghost Admin API 공통 헤더."""
    return {
        "Authorization": f"Ghost {_get_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _resolve_default_target_url() -> str:
    """N8N_WEBHOOK_URL 환경변수를 기반으로 기본 target_url 조립."""
    base = os.environ.get("N8N_WEBHOOK_URL")
    if not base:
        raise RuntimeError(
            "N8N_WEBHOOK_URL 환경변수가 설정되지 않았습니다. "
            "예: export N8N_WEBHOOK_URL=https://n8n.example.com"
        )
    return f"{base.rstrip('/')}{DEFAULT_WEBHOOK_PATH}"


def _validate_target_url(target_url: str) -> None:
    """target_url 은 HTTPS 만 허용."""
    if not target_url.startswith("https://"):
        raise ValueError(
            f"target_url 은 HTTPS 로 시작해야 합니다 (받은 값: {target_url!r}). "
            "보안상 http:// 은 허용되지 않습니다."
        )


def _find_existing(
    webhooks: list[dict[str, Any]],
    event: str,
    target_url: str,
) -> dict[str, Any] | None:
    """같은 event + target_url 조합이 이미 존재하는지 확인."""
    for wh in webhooks:
        if wh.get("event") == event and wh.get("target_url") == target_url:
            return wh
    return None


# --------------------------------------------------------------------------- #
# 퍼블릭 API
# --------------------------------------------------------------------------- #
def list_webhooks() -> list[dict]:
    """GET /admin/webhooks/ → 등록된 webhook 목록."""
    response = requests.get(
        f"{_admin_api_base()}/webhooks/",
        headers=_headers(),
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("webhooks", [])


def register_webhook(
    event: str = DEFAULT_EVENT,
    target_url: str | None = None,
    name: str = DEFAULT_NAME,
) -> dict:
    """
    Ghost Admin API 로 Webhook 을 등록한다.

    - target_url 미지정 시 N8N_WEBHOOK_URL + DEFAULT_WEBHOOK_PATH 로 자동 조립
    - target_url 은 HTTPS 강제
    - 반환: {webhook_id, event, target_url, status}
    """
    resolved = target_url or _resolve_default_target_url()
    _validate_target_url(resolved)

    payload = {
        "webhooks": [
            {
                "event": event,
                "target_url": resolved,
                "name": name,
            }
        ]
    }
    response = requests.post(
        f"{_admin_api_base()}/webhooks/",
        headers=_headers(),
        json=payload,
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    created = response.json().get("webhooks", [{}])[0]
    return {
        "webhook_id": created.get("id", ""),
        "event": created.get("event", event),
        "target_url": created.get("target_url", resolved),
        "status": "registered",
    }


def delete_webhook(webhook_id: str) -> bool:
    """DELETE /admin/webhooks/:id — 성공 시 True."""
    response = requests.delete(
        f"{_admin_api_base()}/webhooks/{webhook_id}/",
        headers=_headers(),
        timeout=HTTP_TIMEOUT,
    )
    if response.status_code in (200, 204):
        return True
    response.raise_for_status()
    return False


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_list() -> int:
    print("=== Ghost Webhook 목록 ===")
    items = list_webhooks()
    if not items:
        print("  ℹ️  등록된 Webhook 이 없습니다.")
        return 0
    print(f"  ℹ️  {len(items)}개 등록되어 있음")
    for wh in items:
        print(
            f"     - id: {wh.get('id')}, event: {wh.get('event')}, "
            f"url: {wh.get('target_url')}"
        )
    print("=== 완료 ===")
    return 0


def _cmd_delete(webhook_id: str) -> int:
    print(f"=== Ghost Webhook 삭제: {webhook_id} ===")
    ok = delete_webhook(webhook_id)
    if ok:
        print(f"  ✅ 삭제 완료: {webhook_id}")
        print("=== 완료 ===")
        return 0
    print(f"  ❌ 삭제 실패: {webhook_id}")
    return 1


def _cmd_register(
    event: str,
    target_url: str | None,
    name: str,
    *,
    dry_run: bool,
    overwrite: bool,
) -> int:
    print("=== Ghost Webhook 등록 ===")

    # target_url 조립 및 검증
    try:
        resolved_target = target_url or _resolve_default_target_url()
        _validate_target_url(resolved_target)
    except (RuntimeError, ValueError) as exc:
        print(f"  ❌ {exc}")
        return 1

    # dry-run: 실제 Ghost 호출 없이 JWT 생성 + 요청 미리보기
    if dry_run:
        try:
            token = _get_token()
        except KeyError as exc:
            print(f"  ❌ 환경변수 누락: {exc}")
            return 1
        print("드라이런 — 실제 Ghost 호출 없이 요청 미리보기")
        print(f"  ✅ JWT 토큰 생성 성공 (length={len(token)}, prefix={token[:16]}...)")
        print(f"  • POST {_admin_api_base()}/webhooks/")
        print("  • Headers:")
        print(f"     Authorization: Ghost <JWT>")
        print(f"     Content-Type: application/json")
        print("  • Body:")
        print(
            f"     {{'webhooks': [{{'event': {event!r}, "
            f"'target_url': {resolved_target!r}, 'name': {name!r}}}]}}"
        )
        print("=== 완료 (dry-run) ===")
        return 0

    # 기존 등록 확인
    print("기존 등록 확인:")
    try:
        existing = list_webhooks()
    except requests.HTTPError as exc:
        print(f"  ❌ 목록 조회 실패: {exc}")
        return 1

    if existing:
        print(f"  ℹ️  {len(existing)}개 등록되어 있음")
        for wh in existing:
            print(
                f"     - id: {wh.get('id')}, event: {wh.get('event')}, "
                f"url: {wh.get('target_url')}"
            )
    else:
        print("  ℹ️  등록된 Webhook 이 없습니다.")

    duplicate = _find_existing(existing, event, resolved_target)
    if duplicate:
        if overwrite:
            dup_id = duplicate.get("id", "")
            print(f"  ⚠️  중복 발견 — 기존 Webhook 삭제 후 재등록: {dup_id}")
            try:
                delete_webhook(dup_id)
            except requests.HTTPError as exc:
                print(f"  ❌ 기존 Webhook 삭제 실패: {exc}")
                return 1
        else:
            print(
                f"  ⚠️  같은 event + target_url 조합이 이미 존재합니다 "
                f"(id: {duplicate.get('id')}). 스킵합니다."
            )
            print("      (덮어쓰려면 --overwrite 옵션을 사용하세요)")
            print("=== 완료 ===")
            return 0

    # 실제 등록
    print("새 Webhook 등록:")
    try:
        result = register_webhook(event=event, target_url=resolved_target, name=name)
    except requests.HTTPError as exc:
        print(f"  ❌ 등록 실패: {exc}")
        if exc.response is not None:
            print(f"     응답: {exc.response.text[:500]}")
        return 1

    print(f"  ✅ id: {result['webhook_id']}, event: {result['event']}")
    print(f"     target: {result['target_url']}")
    print("=== 완료 ===")
    print("n8n workflow_3_sns 가 활성 상태인지 확인하세요.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ghost Webhook 자동 등록 유틸리티 (post.published → n8n)"
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--register", action="store_true", help="Webhook 등록")
    action.add_argument("--list", dest="list_", action="store_true", help="등록된 Webhook 목록 조회")
    action.add_argument("--delete", metavar="WEBHOOK_ID", help="특정 Webhook 삭제")

    parser.add_argument(
        "--event",
        default=DEFAULT_EVENT,
        help=f"Ghost 이벤트 이름 (기본: {DEFAULT_EVENT})",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="Webhook 대상 URL. 미지정 시 N8N_WEBHOOK_URL 로 자동 조립.",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_NAME,
        help=f"Webhook 이름 (기본: {DEFAULT_NAME})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 Ghost 호출 없이 JWT 생성 + 요청 미리보기만 출력",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="같은 event + target_url 조합이 존재하면 삭제 후 재등록",
    )

    args = parser.parse_args(argv)

    if args.list_:
        return _cmd_list()
    if args.delete:
        return _cmd_delete(args.delete)
    # --register
    return _cmd_register(
        event=args.event,
        target_url=args.target_url,
        name=args.name,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    raise SystemExit(main())
