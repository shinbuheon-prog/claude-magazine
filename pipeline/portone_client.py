"""
PortOne v2 API 클라이언트 (TASK_020)
- 국내 정기결제(빌링키) 발급 + 결제 트리거 + 조회 + 취소
- 엔드포인트: https://api.portone.io (v2)
- 인증: Authorization: PortOne {PORTONE_API_SECRET}
- 모든 요청·응답은 logs/portone_{timestamp}.json 로 저장

사용법:
    python pipeline/portone_client.py --dry-run
    python pipeline/portone_client.py issue-key --customer-id cust-001 --card-file card.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Windows 환경에서 한국어/특수문자 출력을 위한 UTF-8 강제 설정
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

PORTONE_BASE_URL = "https://api.portone.io"
HTTP_TIMEOUT = 15


def _get_secret() -> str:
    """PORTONE_API_SECRET 환경변수 — 미설정 시 KeyError 전파."""
    return os.environ["PORTONE_API_SECRET"]


def _get_store_id() -> str:
    return os.environ["PORTONE_STORE_ID"]


def _get_mode() -> str:
    """test | live. 기본 test."""
    return os.environ.get("PORTONE_MODE", "test").lower()


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"PortOne {_get_secret()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _log_call(
    *,
    method: str,
    path: str,
    request_payload: dict[str, Any] | None,
    status_code: int | None,
    response_body: Any,
    error: str | None = None,
) -> Path:
    """요청·응답·상태코드를 logs/portone_{timestamp}.json 으로 저장."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + f"_{uuid.uuid4().hex[:6]}"
    log_path = LOGS_DIR / f"portone_{ts}.json"
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": _get_mode() if os.getenv("PORTONE_API_SECRET") else "unconfigured",
        "method": method,
        "path": path,
        "url": f"{PORTONE_BASE_URL}{path}",
        "request": request_payload,
        "status_code": status_code,
        "response": response_body,
        "error": error,
    }
    try:
        log_path.write_text(
            json.dumps(entry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        # 로깅 실패는 본 호출을 막지 않는다.
        pass
    return log_path


def _request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """공통 요청 래퍼. 응답 JSON 반환. 실패 시 예외 + 로그."""
    url = f"{PORTONE_BASE_URL}{path}"
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=_headers(),
            json=payload,
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        _log_call(
            method=method,
            path=path,
            request_payload=payload,
            status_code=None,
            response_body=None,
            error=f"network error: {exc}",
        )
        raise

    status = response.status_code
    try:
        body: Any = response.json()
    except ValueError:
        body = {"raw_text": response.text}

    _log_call(
        method=method,
        path=path,
        request_payload=payload,
        status_code=status,
        response_body=body,
    )

    if status >= 400:
        raise requests.HTTPError(
            f"PortOne API {method} {path} failed: {status} {body}",
            response=response,
        )
    if isinstance(body, dict):
        return body
    return {"data": body}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def issue_billing_key(customer_id: str, card_info: dict[str, Any]) -> dict[str, Any]:
    """
    PortOne v2 POST /billing-keys 로 빌링키 발급.

    card_info 예시:
        {
            "method": {
                "card": {
                    "credential": {
                        "number": "4242...", "expiryYear": "27", "expiryMonth": "12",
                        "birthOrBusinessRegistrationNumber": "900101",
                        "passwordTwoDigits": "12"
                    }
                }
            }
        }

    반환: {"billing_key": str, "customer_id": str, "expires_at": str | None, "raw": dict}
    """
    payload: dict[str, Any] = {
        "storeId": _get_store_id(),
        "customer": {"id": customer_id},
    }
    # card_info는 PortOne v2 스키마 그대로 병합 (method 필드 포함)
    if "method" in card_info:
        payload["method"] = card_info["method"]
    else:
        payload["method"] = card_info

    body = _request("POST", "/billing-keys", payload=payload)
    billing_key = (
        body.get("billingKey")
        or body.get("billing_key")
        or (body.get("billingKeyInfo") or {}).get("billingKey", "")
    )
    expires_at = (
        body.get("expiresAt")
        or body.get("expires_at")
        or (body.get("billingKeyInfo") or {}).get("expiresAt")
    )
    return {
        "billing_key": billing_key,
        "customer_id": customer_id,
        "expires_at": expires_at,
        "raw": body,
    }


def charge(
    billing_key: str,
    amount: int,
    order_name: str,
    order_id: str,
    *,
    currency: str = "KRW",
    customer_id: str | None = None,
) -> dict[str, Any]:
    """
    PortOne v2 POST /payments/{paymentId}/billing-key-payment 로 즉시 결제.

    PortOne v2는 가맹점에서 고유 paymentId를 발급해 path param으로 전달한다.
    여기서는 order_id를 paymentId로 사용한다.

    반환: {"payment_id": str, "status": "PAID|FAILED|...", "receipt_url": str, "raw": dict}
    """
    payment_id = order_id
    payload: dict[str, Any] = {
        "storeId": _get_store_id(),
        "billingKey": billing_key,
        "orderName": order_name,
        "amount": {"total": int(amount)},
        "currency": currency,
    }
    if customer_id:
        payload["customer"] = {"id": customer_id}

    body = _request("POST", f"/payments/{payment_id}/billing-key-payment", payload=payload)
    # v2 응답은 payment.status 필드 또는 상위 status 중 하나에 들어올 수 있다.
    status = (
        body.get("status")
        or (body.get("payment") or {}).get("status")
        or "UNKNOWN"
    )
    receipt_url = (
        body.get("receiptUrl")
        or (body.get("payment") or {}).get("receiptUrl")
        or ""
    )
    resolved_payment_id = (
        body.get("paymentId")
        or (body.get("payment") or {}).get("id")
        or payment_id
    )
    return {
        "payment_id": resolved_payment_id,
        "status": str(status).upper(),
        "receipt_url": receipt_url or "",
        "raw": body,
    }


def get_payment(payment_id: str) -> dict[str, Any]:
    """GET /payments/{paymentId} — 결제 상세 조회."""
    return _request("GET", f"/payments/{payment_id}")


def cancel_payment(payment_id: str, reason: str) -> dict[str, Any]:
    """
    POST /payments/{paymentId}/cancel — 결제 취소.
    반환: PortOne 원본 응답 dict.
    """
    payload = {
        "storeId": _get_store_id(),
        "reason": reason,
    }
    return _request("POST", f"/payments/{payment_id}/cancel", payload=payload)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _has_required_env() -> bool:
    return bool(os.getenv("PORTONE_API_SECRET") and os.getenv("PORTONE_STORE_ID"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PortOne v2 API 클라이언트 CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_issue = sub.add_parser("issue-key", help="빌링키 발급 (카드 JSON 파일 필요)")
    p_issue.add_argument("--customer-id", required=True)
    p_issue.add_argument("--card-file", required=True, help="card_info JSON 파일 경로")

    p_charge = sub.add_parser("charge", help="빌링키로 즉시 결제")
    p_charge.add_argument("--billing-key", required=True)
    p_charge.add_argument("--amount", type=int, required=True)
    p_charge.add_argument("--order-name", required=True)
    p_charge.add_argument("--order-id", required=True)
    p_charge.add_argument("--customer-id")

    p_get = sub.add_parser("get", help="결제 조회")
    p_get.add_argument("--payment-id", required=True)

    p_cancel = sub.add_parser("cancel", help="결제 취소")
    p_cancel.add_argument("--payment-id", required=True)
    p_cancel.add_argument("--reason", required=True)

    parser.add_argument("--dry-run", action="store_true", help="환경변수/구조만 검증 (실제 호출 없음)")
    args = parser.parse_args(argv)

    if args.dry_run or not _has_required_env():
        info = {
            "mode": "dry-run",
            "cmd": args.cmd,
            "base_url": PORTONE_BASE_URL,
            "store_id_configured": bool(os.getenv("PORTONE_STORE_ID")),
            "api_secret_configured": bool(os.getenv("PORTONE_API_SECRET")),
            "portone_mode": _get_mode() if os.getenv("PORTONE_API_SECRET") else "unconfigured",
        }
        print(json.dumps(info, ensure_ascii=False, indent=2))
        if not args.dry_run and not _has_required_env():
            print(
                "PORTONE_STORE_ID + PORTONE_API_SECRET 미설정. "
                ".env 에 값을 채우거나 --dry-run 으로 실행하세요.",
                file=sys.stderr,
            )
        return 0

    if args.cmd == "issue-key":
        card_info = json.loads(Path(args.card_file).read_text(encoding="utf-8"))
        result = issue_billing_key(args.customer_id, card_info)
    elif args.cmd == "charge":
        result = charge(
            args.billing_key,
            args.amount,
            args.order_name,
            args.order_id,
            customer_id=args.customer_id,
        )
    elif args.cmd == "get":
        result = get_payment(args.payment_id)
    elif args.cmd == "cancel":
        result = cancel_payment(args.payment_id, args.reason)
    else:
        parser.print_help()
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    # 스모크 테스트: 환경변수 없어도 구조 검증만 수행 (--dry-run)
    raise SystemExit(main())
