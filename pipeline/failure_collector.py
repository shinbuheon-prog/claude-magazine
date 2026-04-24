"""
failure_collector.py — TASK_027 자율 개선 루프 실패 통합 수집기

5개 소스에서 7일치 실패를 모아 단일 딕셔너리로 반환한다:
  1) logs/*.json (editorial_lint·brief·factcheck 실패 기록)
  2) data/editor_corrections.db (TASK_026 편집자 판정)
  3) Langfuse API (LANGFUSE_ENABLED=True 시)
  4) Ghost Content API (발행 기사 목록, 키 없으면 skip)
  5) standards_checker 실패 (TASK_025 기반)

사용법:
    python pipeline/failure_collector.py --since-days 7
    python pipeline/failure_collector.py --since-days 14 --out logs/failures.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

if sys.platform == "win32" and not getattr(sys.stdout, "_cm_utf8", False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        sys.stdout._cm_utf8 = True  # type: ignore[attr-defined]
        sys.stderr._cm_utf8 = True  # type: ignore[attr-defined]
    except (ValueError, AttributeError):
        pass

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
CORRECTIONS_DB = DATA_DIR / "editor_corrections.db"

NETWORK_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 15
MAX_EXAMPLES = 5


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _scrub(value: Any) -> Any:
    """PII/시크릿 스크러빙 — 이메일·API 키·Bearer 토큰 마스킹."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if not isinstance(value, str):
        return value

    text = value
    # 이메일 주소
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<email>", text)
    # sk-ant-*, sk_live_* 류 API 키
    text = re.sub(r"sk[-_](?:ant|live|test)[-_][A-Za-z0-9_\-]{10,}", "<api-key>", text, flags=re.IGNORECASE)
    # Bearer / Authorization 헤더
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._\-]{10,}", "bearer <token>", text)
    # LANGFUSE/ANTHROPIC_API_KEY=... 같은 환경변수 노출
    text = re.sub(
        r"(ANTHROPIC_API_KEY|LANGFUSE_SECRET_KEY|LANGFUSE_PUBLIC_KEY|GHOST_[A-Z_]+)\s*=\s*\S+",
        r"\1=<redacted>",
        text,
    )
    return text


def _since_cutoff(since_days: int) -> datetime:
    return _utc_now() - timedelta(days=since_days)


# ---------------------------------------------------------------------------
# 1) logs/*.json 수집 — editorial_lint / brief / factcheck 실패 JSON
# ---------------------------------------------------------------------------


def _log_file_timestamp(path: Path) -> datetime | None:
    """파일명 brief_YYYYMMDD_HHMMSS.json 또는 mtime 기반으로 타임스탬프 추출."""
    match = re.search(r"(\d{8})_(\d{6})", path.stem)
    if match:
        try:
            return datetime.strptime(
                f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def collect_log_failures(since_days: int) -> dict[str, Any]:
    """logs/*.json을 스캔해 editorial_lint·팩트체크 실패를 집계."""
    if not LOGS_DIR.exists():
        return {"editorial_lint_failures": [], "factcheck_summary": {}}

    cutoff = _since_cutoff(since_days)
    lint_counter: Counter[str] = Counter()
    lint_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    factcheck_count = 0
    factcheck_request_ids: list[str] = []

    for path in LOGS_DIR.glob("*.json"):
        ts = _log_file_timestamp(path)
        if ts and ts < cutoff:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        # editorial_lint 결과: {"items": [{"id", "status", "message"}, ...]}
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("status") == "fail":
                    check_id = str(item.get("id") or "unknown")
                    lint_counter[check_id] += 1
                    if len(lint_examples[check_id]) < MAX_EXAMPLES:
                        lint_examples[check_id].append(
                            {
                                "file": path.name,
                                "message": _scrub(item.get("message", "")),
                            }
                        )

        # factcheck 로그: {"model": "claude-opus-4-7", "request_id": ..., ...}
        if path.name.startswith("factcheck_"):
            factcheck_count += 1
            rid = data.get("request_id")
            if rid:
                factcheck_request_ids.append(str(rid))

    editorial_lint_failures = [
        {
            "check_id": check_id,
            "count": count,
            "examples": lint_examples.get(check_id, []),
        }
        for check_id, count in lint_counter.most_common()
    ]

    return {
        "editorial_lint_failures": editorial_lint_failures,
        "factcheck_summary": {
            "total_runs": factcheck_count,
            "sample_request_ids": factcheck_request_ids[:MAX_EXAMPLES],
        },
    }


# ---------------------------------------------------------------------------
# 2) editor_corrections.db 수집 (TASK_026)
# ---------------------------------------------------------------------------


def collect_editor_corrections(since_days: int) -> list[dict[str, Any]]:
    """data/editor_corrections.db에서 correction_type별 통계 산출."""
    if not CORRECTIONS_DB.exists():
        return []

    cutoff = _since_cutoff(since_days).isoformat()
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(CORRECTIONS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT correction_type, severity, category, original_text, corrected_text,
                   editor_note, timestamp
            FROM corrections
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            """,
            (cutoff,),
        ).fetchall()
    except sqlite3.Error as exc:
        print(f"[warn] editor_corrections DB 조회 실패: {exc}", file=sys.stderr)
        return []
    finally:
        if conn is not None:
            conn.close()

    by_type: dict[str, dict[str, Any]] = {}
    examples_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        ctype = row["correction_type"]
        bucket = by_type.setdefault(
            ctype,
            {
                "type": ctype,
                "count": 0,
                "severity_high_count": 0,
                "categories": Counter(),
                "examples": [],
            },
        )
        bucket["count"] += 1
        if row["severity"] == "high":
            bucket["severity_high_count"] += 1
        if row["category"]:
            bucket["categories"][row["category"]] += 1
        if len(examples_by_type[ctype]) < MAX_EXAMPLES:
            examples_by_type[ctype].append(
                {
                    "original": _scrub(row["original_text"]),
                    "corrected": _scrub(row["corrected_text"]),
                    "severity": row["severity"],
                    "category": row["category"],
                    "note": _scrub(row["editor_note"]),
                }
            )

    result: list[dict[str, Any]] = []
    for ctype, bucket in by_type.items():
        result.append(
            {
                "type": ctype,
                "count": bucket["count"],
                "severity_high_count": bucket["severity_high_count"],
                "top_categories": bucket["categories"].most_common(3),
                "examples": examples_by_type[ctype],
            }
        )
    result.sort(key=lambda item: item["count"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# 3) Langfuse 이상 메트릭 (있으면)
# ---------------------------------------------------------------------------


def collect_langfuse_anomalies(since_days: int) -> list[dict[str, Any]]:
    """LANGFUSE_ENABLED일 때 최근 N일 대비 baseline(이전 N일) 비교."""
    try:
        from pipeline.observability import LANGFUSE_ENABLED, _lf  # type: ignore
    except ModuleNotFoundError:
        try:
            from observability import LANGFUSE_ENABLED, _lf  # type: ignore
        except ModuleNotFoundError:
            return []

    if not LANGFUSE_ENABLED or _lf is None:
        return []

    end = _utc_now()
    current_start = end - timedelta(days=since_days)
    baseline_start = current_start - timedelta(days=since_days)

    def _fetch_traces(start: datetime, stop: datetime) -> list[Any]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = _lf.fetch_traces(
                    from_timestamp=start,
                    to_timestamp=stop,
                    limit=200,
                )
                data = getattr(response, "data", None) or response
                return list(data) if data else []
            except Exception as exc:  # pragma: no cover — 네트워크
                print(
                    f"[warn] Langfuse fetch 실패 (attempt {attempt}/{MAX_RETRIES}): {exc}",
                    file=sys.stderr,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_WAIT_SECONDS)
        return []

    current = _fetch_traces(current_start, end)
    baseline = _fetch_traces(baseline_start, current_start)

    def _avg_latency(traces: list[Any]) -> float:
        values: list[float] = []
        for trace in traces:
            lat = getattr(trace, "latency", None)
            if lat is None and isinstance(trace, dict):
                lat = trace.get("latency")
            if isinstance(lat, (int, float)):
                values.append(float(lat))
        return sum(values) / len(values) if values else 0.0

    anomalies: list[dict[str, Any]] = []
    cur_avg = _avg_latency(current)
    base_avg = _avg_latency(baseline)
    if base_avg > 0:
        delta_pct = round(((cur_avg - base_avg) / base_avg) * 100, 1)
        if abs(delta_pct) >= 20:
            anomalies.append(
                {
                    "metric": "avg_latency_seconds",
                    "baseline": round(base_avg, 2),
                    "current": round(cur_avg, 2),
                    "delta_pct": delta_pct,
                }
            )

    cur_count = len(current)
    base_count = len(baseline)
    if base_count > 0:
        vol_delta = round(((cur_count - base_count) / base_count) * 100, 1)
        if abs(vol_delta) >= 30:
            anomalies.append(
                {
                    "metric": "trace_volume",
                    "baseline": base_count,
                    "current": cur_count,
                    "delta_pct": vol_delta,
                }
            )

    return anomalies


# ---------------------------------------------------------------------------
# 4) Ghost Content API — 발행 완료 기사 수
# ---------------------------------------------------------------------------


def collect_ghost_publications(since_days: int) -> int:
    """Ghost Content API로 최근 발행 기사 수 조회. 키 없으면 0."""
    api_url = os.getenv("GHOST_CONTENT_API_URL") or os.getenv("GHOST_API_URL")
    api_key = os.getenv("GHOST_CONTENT_API_KEY")
    if not api_url or not api_key:
        return 0

    try:
        import requests
    except ImportError:
        return 0

    cutoff = _since_cutoff(since_days).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    endpoint = api_url.rstrip("/") + "/posts/"
    params = {
        "key": api_key,
        "filter": f"published_at:>={cutoff}",
        "limit": "100",
        "fields": "id,published_at",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(endpoint, params=params, timeout=NETWORK_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return len(data.get("posts", []))
        except Exception as exc:  # pragma: no cover
            print(
                f"[warn] Ghost Content API 실패 (attempt {attempt}/{MAX_RETRIES}): {type(exc).__name__}",
                file=sys.stderr,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)
    return 0


# ---------------------------------------------------------------------------
# 5) standards_checker 실패 (TASK_025) — logs/*.json에 embed된 결과 기반
# ---------------------------------------------------------------------------


def collect_standards_failures(since_days: int) -> list[dict[str, Any]]:
    """logs/*.json에서 standards_checker 결과(article-standards 실패)를 집계."""
    if not LOGS_DIR.exists():
        return []

    cutoff = _since_cutoff(since_days)
    rule_counter: Counter[str] = Counter()
    rule_category: dict[str, Counter] = defaultdict(Counter)
    examples_by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path in LOGS_DIR.glob("*.json"):
        ts = _log_file_timestamp(path)
        if ts and ts < cutoff:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue

        category = data.get("category") or ""

        # 직접 standards_checker 출력 포맷
        for bucket_key in ("common_checks", "category_checks", "should_checks"):
            for item in data.get(bucket_key, []) or []:
                if not isinstance(item, dict):
                    continue
                if item.get("status") == "fail":
                    rule_id = str(item.get("id") or "unknown")
                    rule_counter[rule_id] += 1
                    rule_category[rule_id][category or "unknown"] += 1
                    if len(examples_by_rule[rule_id]) < MAX_EXAMPLES:
                        examples_by_rule[rule_id].append(
                            {
                                "file": path.name,
                                "rule": _scrub(item.get("rule", "")),
                                "measured": _scrub(item.get("measured", "")),
                                "expected": _scrub(item.get("expected", "")),
                            }
                        )

        # editorial_lint에 embed된 article-standards 실패
        for item in data.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            if item.get("id") == "article-standards" and item.get("status") == "fail":
                for detail in item.get("details") or []:
                    rule_counter[str(detail)] += 1

    result: list[dict[str, Any]] = []
    for rule_id, count in rule_counter.most_common():
        result.append(
            {
                "rule_id": rule_id,
                "category": rule_category[rule_id].most_common(1)[0][0]
                if rule_category[rule_id]
                else "unknown",
                "count": count,
                "examples": examples_by_rule.get(rule_id, []),
            }
        )
    return result


# ---------------------------------------------------------------------------
# 통합 collect_failures
# ---------------------------------------------------------------------------


def collect_failures(since_days: int = 7) -> dict[str, Any]:
    """5개 소스에서 실패 데이터를 모아 단일 딕셔너리로 반환."""
    end = _utc_now()
    start = _since_cutoff(since_days)

    log_data = collect_log_failures(since_days)
    corrections = collect_editor_corrections(since_days)
    standards_failures = collect_standards_failures(since_days)
    langfuse_anomalies = collect_langfuse_anomalies(since_days)
    total_articles = collect_ghost_publications(since_days)

    return {
        "period": {"from": start.isoformat(), "to": end.isoformat(), "days": since_days},
        "editorial_lint_failures": log_data["editorial_lint_failures"],
        "factcheck_summary": log_data["factcheck_summary"],
        "standards_failures": standards_failures,
        "editor_corrections": corrections,
        "langfuse_anomalies": langfuse_anomalies,
        "total_articles": total_articles,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli_run(args: argparse.Namespace) -> int:
    failures = collect_failures(since_days=args.since_days)
    payload = json.dumps(failures, ensure_ascii=False, indent=2, default=str)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"[ok] failures written to {out_path}")
    else:
        print(payload)
    return 0


def _smoke_test() -> None:
    """가짜 데이터에 의존하지 않는 스모크 — 실제 DB·로그가 없어도 동작."""
    failures = collect_failures(since_days=7)
    assert "period" in failures
    assert "editorial_lint_failures" in failures
    assert "editor_corrections" in failures
    assert "standards_failures" in failures
    assert "total_articles" in failures
    print("ok failure_collector 스모크 테스트 통과 (7일치 수집 구조 검증)")


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK_027 실패 통합 수집기")
    parser.add_argument("--since-days", type=int, default=7, help="최근 N일 수집 (기본 7)")
    parser.add_argument("--out", help="결과를 파일로 저장 (생략 시 stdout)")
    parser.add_argument("--dry-run", action="store_true", help="스모크 테스트 수행")
    args = parser.parse_args()

    if args.dry_run:
        _smoke_test()
        return 0
    return _cli_run(args)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _smoke_test()
    else:
        raise SystemExit(main())
