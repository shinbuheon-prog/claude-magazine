"""Monthly illustration budget audit.

매거진 무료 발행 원칙(`CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=0.0` 기본값)을
기술적으로 강제하기 위한 감시 도구. illustration_hook가 누적한
`data/illustration_cost_<YYYY-MM>.json`을 읽고 cap 초과 여부를 판정한다.

사용법:
    python scripts/audit_budget.py                    # 이번 달, 텍스트 출력
    python scripts/audit_budget.py --month 2026-04    # 특정 달
    python scripts/audit_budget.py --json             # JSON 출력
    python scripts/audit_budget.py --strict           # cap 초과 시 exit 1
    python scripts/audit_budget.py --notify           # >=80% 시 Slack 알림
    python scripts/audit_budget.py --cap 5.0          # cap 임시 override

CI 통합 예시:
    - name: Audit illustration budget
      run: python scripts/audit_budget.py --strict --notify
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if (
    sys.platform == "win32"
    and "pytest" not in sys.modules
    and not getattr(sys.stdout, "_cm_utf8", False)
):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        sys.stderr._cm_utf8 = True  # type: ignore[attr-defined]
    except (ValueError, AttributeError):
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COST_TRACKING_DIR = DATA_DIR / "cost_tracking"
COST_TRACKING_DIR.mkdir(parents=True, exist_ok=True)

WARN_THRESHOLD = 0.8  # 80% utilization 시 Slack 알림
DEFAULT_CAP = 0.0  # 무료 발행 원칙 기본값


DEFAULT_ARTICLE_BUDGET_USD = 1.0
DEFAULT_G5_THRESHOLD_PCT = 150.0


def _illustration_cost_path(month: str) -> Path:
    return DATA_DIR / f"illustration_cost_{month}.json"


def _article_cost_path(article_id: str) -> Path:
    safe_article_id = str(article_id).replace("/", "-").replace("\\", "-")
    return COST_TRACKING_DIR / f"article_{safe_article_id}_costs.json"


def read_illustration_cost(month: str) -> dict[str, Any]:
    """data/illustration_cost_<month>.json 읽기. 없으면 zero 페이로드."""
    path = _illustration_cost_path(month)
    if not path.exists():
        return {"month": month, "total_usd": 0.0, "providers": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"month": month, "total_usd": 0.0, "providers": {}}


def read_article_cost(article_id: str) -> dict[str, Any]:
    path = _article_cost_path(article_id)
    if not path.exists():
        return {
            "article_id": article_id,
            "estimated_budget_usd": resolve_article_budget(),
            "actual_costs": {},
            "total_cost_usd": 0.0,
            "budget_utilization_pct": 0.0,
            "g5_triggered": False,
            "editor_decision": None,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        payload = {"article_id": article_id}
    payload.setdefault("article_id", article_id)
    payload.setdefault("estimated_budget_usd", resolve_article_budget())
    payload.setdefault("actual_costs", {})
    payload.setdefault("total_cost_usd", 0.0)
    payload.setdefault("budget_utilization_pct", 0.0)
    payload.setdefault("g5_triggered", False)
    payload.setdefault("editor_decision", None)
    return payload


def write_article_cost(article_id: str, payload: dict[str, Any]) -> Path:
    path = _article_cost_path(article_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def resolve_cap(override: float | None = None) -> float:
    """CAP 결정. override > env > DEFAULT_CAP. 음수·invalid는 0으로 clamp."""
    if override is not None:
        return max(0.0, float(override))
    raw = os.environ.get("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", str(DEFAULT_CAP))
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_CAP


def resolve_article_budget(override: float | None = None) -> float:
    if override is not None:
        return max(0.0, float(override))
    raw = os.environ.get("ARTICLE_BUDGET_DEFAULT_USD", str(DEFAULT_ARTICLE_BUDGET_USD))
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_ARTICLE_BUDGET_USD


def resolve_g5_threshold_pct(override: float | None = None) -> float:
    if override is not None:
        return max(0.0, float(override))
    raw = os.environ.get("G5_THRESHOLD_PCT", str(DEFAULT_G5_THRESHOLD_PCT))
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_G5_THRESHOLD_PCT


def utilization(total: float, cap: float) -> float | None:
    """cap=0이면 None (무료-only 모드는 비율 의미 없음)."""
    if cap <= 0:
        return None
    return total / cap


def render_text(month: str, cost: dict[str, Any], cap: float) -> str:
    total = float(cost.get("total_usd") or 0.0)
    util = utilization(total, cap)
    lines = [
        f"=== Illustration Budget Audit ({month}) ===",
        f"  Cap:           ${cap:.4f}",
        f"  Used:          ${total:.4f}",
    ]
    if util is None:
        lines.append("  Utilization:   n/a (cap=0, free-only mode)")
    else:
        lines.append(f"  Utilization:   {util:.1%}")

    providers = cost.get("providers") or {}
    if providers:
        lines.append("")
        lines.append("  By Provider:")
        for provider, amount in sorted(providers.items()):
            lines.append(f"    {provider}: ${float(amount):.4f}")

    if cap > 0 and total > cap:
        lines.append("")
        lines.append(f"  ⚠️ EXCEEDED — used ${total - cap:.4f} over cap")
    elif util is not None and util >= WARN_THRESHOLD:
        lines.append("")
        lines.append(f"  ⚠️ APPROACHING — {util:.1%} of cap reached")
    return "\n".join(lines)


def render_json(month: str, cost: dict[str, Any], cap: float) -> dict[str, Any]:
    total = float(cost.get("total_usd") or 0.0)
    util = utilization(total, cap)
    return {
        "month": month,
        "total_usd": total,
        "cap_usd": cap,
        "utilization": util,
        "providers": cost.get("providers", {}),
        "exceeded": cap > 0 and total > cap,
        "approaching": util is not None and util >= WARN_THRESHOLD,
    }


def check_article_budget(article_id: str, threshold_pct: float | None = None) -> dict[str, Any]:
    payload = read_article_cost(article_id)
    budget = max(0.0, float(payload.get("estimated_budget_usd") or resolve_article_budget()))
    total = max(0.0, float(payload.get("total_cost_usd") or 0.0))
    threshold = resolve_g5_threshold_pct(threshold_pct)
    utilization_pct = 0.0 if budget <= 0 else (total / budget) * 100.0
    triggered = utilization_pct >= threshold if budget > 0 else total > 0

    payload["estimated_budget_usd"] = budget
    payload["total_cost_usd"] = total
    payload["budget_utilization_pct"] = utilization_pct
    payload["g5_triggered"] = triggered
    write_article_cost(article_id, payload)

    return {
        "article_id": article_id,
        "current_cost_usd": total,
        "budget_usd": budget,
        "utilization_pct": utilization_pct,
        "threshold_pct": threshold,
        "g5_triggered": triggered,
        "action_required": "editor_decision" if triggered else None,
        "editor_decision": payload.get("editor_decision"),
        "path": str(_article_cost_path(article_id)),
    }


def notify_slack(month: str, total: float, cap: float, util: float | None) -> None:
    """80% 이상 utilization 시 Slack webhook 발송. 미설정·실패는 silent skip."""
    webhook = os.environ.get("NOTIFY_SLACK_WEBHOOK")
    if not webhook:
        return
    if util is None or util < WARN_THRESHOLD:
        return
    try:
        import requests
    except ImportError:
        return
    severity = "EXCEEDED" if cap > 0 and total > cap else "APPROACHING"
    text = (
        f"⚠️ Illustration budget {severity} for {month} — "
        f"${total:.2f} / ${cap:.2f} ({util:.1%})"
    )
    try:
        requests.post(webhook, json={"text": text}, timeout=10)
    except Exception as exc:  # pragma: no cover
        print(f"[warn] Slack notify failed: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Monthly illustration budget audit")
    parser.add_argument("--month", help="YYYY-MM (default: 이번 달, UTC)")
    parser.add_argument("--cap", type=float, help="CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP override")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--notify", action="store_true", help=f">={int(WARN_THRESHOLD*100)} percent 시 Slack 알림")
    parser.add_argument("--strict", action="store_true", help="cap 초과 시 exit 1")
    args = parser.parse_args()

    month = args.month or datetime.now(timezone.utc).strftime("%Y-%m")
    cost = read_illustration_cost(month)
    cap = resolve_cap(args.cap)
    total = float(cost.get("total_usd") or 0.0)
    util = utilization(total, cap)

    if args.json:
        print(json.dumps(render_json(month, cost, cap), ensure_ascii=False, indent=2))
    else:
        print(render_text(month, cost, cap))

    if args.notify:
        notify_slack(month, total, cap, util)

    if args.strict and cap > 0 and total > cap:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
