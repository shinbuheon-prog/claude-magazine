"""
Collect failure and operational signals for the weekly improvement loop.

Usage:
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

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
CORRECTIONS_DB = DATA_DIR / "editor_corrections.db"

NETWORK_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 15
MAX_EXAMPLES = 5
LINT_CITATIONS_CHECK_ID = "citations-cross-check"
PIPELINE_PREFIXES = {
    "factcheck": "fact_checker",
    "brief": "brief_generator",
    "draft": "draft_writer",
    "lint": "editorial_lint",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _since_cutoff(since_days: int) -> datetime:
    return _utc_now() - timedelta(days=since_days)


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _log_file_timestamp(path: Path) -> datetime | None:
    match = re.search(r"(\d{8})_(\d{6})", path.stem)
    if match:
        try:
            return datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def _payload_timestamp(path: Path, payload: dict[str, Any]) -> datetime | None:
    return (
        _parse_iso8601(str(payload.get("timestamp") or payload.get("last_updated") or ""))
        or _log_file_timestamp(path)
    )


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _scrub(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if not isinstance(value, str):
        return value

    text = value
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<email>", text)
    text = re.sub(r"sk[-_](?:ant|live|test)[-_][A-Za-z0-9_\-]{10,}", "<api-key>", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._\-]{10,}", "bearer <token>", text)
    text = re.sub(
        r"(ANTHROPIC_API_KEY|LANGFUSE_SECRET_KEY|LANGFUSE_PUBLIC_KEY|GHOST_[A-Z_]+)\s*=\s*\S+",
        r"\1=<redacted>",
        text,
    )
    return text


def _daily_range(days: int, now: datetime | None = None) -> list[str]:
    base = now or _utc_now()
    return [(base - timedelta(days=offset)).date().isoformat() for offset in range(days - 1, -1, -1)]


def _float_mean(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def _derive_article_id(path: Path, payload: dict[str, Any]) -> str:
    explicit = str(payload.get("article_id") or payload.get("draft_id") or "").strip()
    if explicit:
        return explicit
    stem = path.stem
    parts = stem.split("_")
    if len(parts) >= 3:
        return "_".join(parts[1:])
    if len(parts) == 2:
        return parts[1]
    return stem


def _signed_percent_text(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.0f}%"


def collect_log_failures(since_days: int) -> dict[str, Any]:
    if not LOGS_DIR.exists():
        return {"editorial_lint_failures": [], "factcheck_summary": {}}

    cutoff = _since_cutoff(since_days)
    lint_counter: Counter[str] = Counter()
    lint_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    factcheck_count = 0
    factcheck_request_ids: list[str] = []

    for path in LOGS_DIR.glob("*.json"):
        payload = _safe_read_json(path)
        if payload is None:
            continue
        timestamp = _payload_timestamp(path, payload)
        if timestamp is not None and timestamp < cutoff:
            continue

        items = payload.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("status") == "fail":
                    check_id = str(item.get("id") or "unknown")
                    lint_counter[check_id] += 1
                    if len(lint_examples[check_id]) < MAX_EXAMPLES:
                        lint_examples[check_id].append(
                            {"file": path.name, "message": _scrub(item.get("message", ""))}
                        )

        if path.name.startswith("factcheck_"):
            factcheck_count += 1
            request_id = payload.get("request_id")
            if request_id:
                factcheck_request_ids.append(str(request_id))

    return {
        "editorial_lint_failures": [
            {
                "check_id": check_id,
                "count": count,
                "examples": lint_examples.get(check_id, []),
            }
            for check_id, count in lint_counter.most_common()
        ],
        "factcheck_summary": {
            "total_runs": factcheck_count,
            "sample_request_ids": factcheck_request_ids[:MAX_EXAMPLES],
        },
    }


def collect_editor_corrections(since_days: int) -> list[dict[str, Any]]:
    if not CORRECTIONS_DB.exists():
        return []

    cutoff = _since_cutoff(since_days).isoformat()
    rows: list[sqlite3.Row] = []
    try:
        with sqlite3.connect(CORRECTIONS_DB) as conn:
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
        print(f"[warn] editor_corrections DB query failed: {exc}", file=sys.stderr)
        return []

    grouped: dict[str, dict[str, Any]] = {}
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        correction_type = str(row["correction_type"])
        bucket = grouped.setdefault(
            correction_type,
            {
                "type": correction_type,
                "count": 0,
                "severity_high_count": 0,
                "categories": Counter(),
            },
        )
        bucket["count"] += 1
        if row["severity"] == "high":
            bucket["severity_high_count"] += 1
        if row["category"]:
            bucket["categories"][row["category"]] += 1
        if len(examples[correction_type]) < MAX_EXAMPLES:
            examples[correction_type].append(
                {
                    "original": _scrub(row["original_text"]),
                    "corrected": _scrub(row["corrected_text"]),
                    "severity": row["severity"],
                    "category": row["category"],
                    "note": _scrub(row["editor_note"]),
                }
            )

    result: list[dict[str, Any]] = []
    for correction_type, bucket in grouped.items():
        result.append(
            {
                "type": correction_type,
                "count": bucket["count"],
                "severity_high_count": bucket["severity_high_count"],
                "top_categories": bucket["categories"].most_common(3),
                "examples": examples[correction_type],
            }
        )
    result.sort(key=lambda item: item["count"], reverse=True)
    return result


def collect_langfuse_anomalies(since_days: int) -> list[dict[str, Any]]:
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
                response = _lf.fetch_traces(from_timestamp=start, to_timestamp=stop, limit=200)
                data = getattr(response, "data", None) or response
                return list(data) if data else []
            except Exception as exc:  # pragma: no cover
                print(f"[warn] Langfuse fetch failed ({attempt}/{MAX_RETRIES}): {exc}", file=sys.stderr)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_WAIT_SECONDS)
        return []

    current = _fetch_traces(current_start, end)
    baseline = _fetch_traces(baseline_start, current_start)

    def _avg_latency(traces: list[Any]) -> float:
        values: list[float] = []
        for trace in traces:
            latency = getattr(trace, "latency", None)
            if latency is None and isinstance(trace, dict):
                latency = trace.get("latency")
            if isinstance(latency, (int, float)):
                values.append(float(latency))
        return sum(values) / len(values) if values else 0.0

    anomalies: list[dict[str, Any]] = []
    current_avg = _avg_latency(current)
    baseline_avg = _avg_latency(baseline)
    if baseline_avg > 0:
        delta_pct = round(((current_avg - baseline_avg) / baseline_avg) * 100, 1)
        if abs(delta_pct) >= 20:
            anomalies.append(
                {
                    "metric": "avg_latency_seconds",
                    "baseline": round(baseline_avg, 2),
                    "current": round(current_avg, 2),
                    "delta_pct": delta_pct,
                }
            )

    if baseline:
        current_count = len(current)
        baseline_count = len(baseline)
        delta_pct = round(((current_count - baseline_count) / baseline_count) * 100, 1)
        if abs(delta_pct) >= 30:
            anomalies.append(
                {
                    "metric": "trace_volume",
                    "baseline": baseline_count,
                    "current": current_count,
                    "delta_pct": delta_pct,
                }
            )
    return anomalies


def collect_ghost_publications(since_days: int) -> int:
    api_url = os.getenv("GHOST_CONTENT_API_URL") or os.getenv("GHOST_API_URL")
    api_key = os.getenv("GHOST_CONTENT_API_KEY")
    if not api_url or not api_key:
        return 0

    try:
        import requests
    except ImportError:
        return 0

    cutoff = _since_cutoff(since_days).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    params = {"key": api_key, "filter": f"published_at:>={cutoff}", "limit": "100", "fields": "id,published_at"}
    endpoint = api_url.rstrip("/") + "/posts/"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(endpoint, params=params, timeout=NETWORK_TIMEOUT)
            response.raise_for_status()
            return len((response.json() or {}).get("posts", []))
        except Exception as exc:  # pragma: no cover
            print(f"[warn] Ghost Content API failed ({attempt}/{MAX_RETRIES}): {type(exc).__name__}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)
    return 0


def collect_standards_failures(since_days: int) -> list[dict[str, Any]]:
    if not LOGS_DIR.exists():
        return []

    cutoff = _since_cutoff(since_days)
    rule_counter: Counter[str] = Counter()
    rule_category: dict[str, Counter[str]] = defaultdict(Counter)
    examples_by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for path in LOGS_DIR.glob("*.json"):
        payload = _safe_read_json(path)
        if payload is None:
            continue
        timestamp = _payload_timestamp(path, payload)
        if timestamp is not None and timestamp < cutoff:
            continue
        category = str(payload.get("category") or "")

        for bucket_key in ("common_checks", "category_checks", "should_checks"):
            for item in payload.get(bucket_key, []) or []:
                if not isinstance(item, dict) or item.get("status") != "fail":
                    continue
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

        for item in payload.get("items", []) or []:
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
                "category": rule_category[rule_id].most_common(1)[0][0] if rule_category[rule_id] else "unknown",
                "count": count,
                "examples": examples_by_rule.get(rule_id, []),
            }
        )
    return result


def collect_cache_signals(since_days: int) -> dict[str, Any]:
    lookback_days = max(since_days, 14)
    cutoff = _since_cutoff(lookback_days)
    days = _daily_range(lookback_days)
    pipelines: dict[str, dict[str, Any]] = {
        name: {
            "runs": 0,
            "cache_enabled_runs": 0,
            "creation": {day: 0 for day in days},
            "read": {day: 0 for day in days},
        }
        for name in PIPELINE_PREFIXES.values()
    }

    if LOGS_DIR.exists():
        for path in LOGS_DIR.glob("*.json"):
            payload = _safe_read_json(path)
            if payload is None:
                continue
            event_type = path.stem.split("_", 1)[0]
            pipeline_name = PIPELINE_PREFIXES.get(event_type)
            if pipeline_name is None:
                continue
            timestamp = _payload_timestamp(path, payload)
            if timestamp is not None and timestamp < cutoff:
                continue
            creation = int(payload.get("cache_creation_input_tokens") or 0)
            read = int(payload.get("cache_read_input_tokens") or 0)
            enabled = bool(payload.get("cache_enabled")) or creation > 0 or read > 0
            bucket = pipelines[pipeline_name]
            bucket["runs"] += 1
            if enabled:
                bucket["cache_enabled_runs"] += 1
            if timestamp is not None:
                day = timestamp.date().isoformat()
                if day in bucket["creation"]:
                    bucket["creation"][day] += creation
                    bucket["read"][day] += read

    result: dict[str, Any] = {}
    for pipeline_name, bucket in pipelines.items():
        trend: list[dict[str, Any]] = []
        for day in days:
            creation = bucket["creation"][day]
            read = bucket["read"][day]
            denom = creation + read
            trend.append({"date": day, "hit_rate": round(read / denom, 4) if denom else 0.0})

        recent = [item["hit_rate"] for item in trend[-7:]]
        previous = [item["hit_rate"] for item in trend[-14:-7]]
        change = None
        if bucket["runs"] >= 3:
            recent_avg = _float_mean(recent)
            previous_avg = _float_mean(previous)
            if recent_avg is not None and previous_avg is not None:
                change = round(recent_avg - previous_avg, 4)

        anomaly = "insufficient_data"
        if change is not None:
            if change <= -0.2:
                anomaly = "degrading"
            elif change >= 0.2:
                anomaly = "improving"
            else:
                anomaly = "stable"

        result[pipeline_name] = {
            "runs": bucket["runs"],
            "cache_enabled_runs": bucket["cache_enabled_runs"],
            "hit_rate_trend": trend,
            "hit_rate_change_7d": change,
            "anomaly": anomaly,
        }

    return {"pipelines": result}


def _classify_citations_status(item: dict[str, Any]) -> str:
    status = str(item.get("status") or "").lower()
    message = str(item.get("message") or "").lower()
    if status == "pass":
        return "pass"
    if status == "fail":
        return "fail"
    if "not backed" in message or "manual source_id" in message or "mismatch" in message:
        return "warn-mismatch"
    return "warn-missing"


def collect_citations_signals(since_days: int) -> dict[str, Any]:
    lookback_days = max(since_days, 14)
    cutoff = _since_cutoff(lookback_days)
    days = _daily_range(14)
    buckets = {day: {"date": day, "pass": 0, "warn": 0, "fail": 0} for day in days}
    counts = {"pass": 0, "warn-missing": 0, "warn-mismatch": 0, "fail": 0}
    mismatched_article_ids: Counter[str] = Counter()
    previous_warn_mismatch = 0
    recent_warn_mismatch = 0
    total = 0

    if LOGS_DIR.exists():
        for path in LOGS_DIR.glob("*.json"):
            payload = _safe_read_json(path)
            if payload is None:
                continue
            items = payload.get("items")
            if not isinstance(items, list):
                continue
            timestamp = _payload_timestamp(path, payload)
            if timestamp is not None and timestamp < cutoff:
                continue
            citations_item = next(
                (item for item in items if isinstance(item, dict) and item.get("id") == LINT_CITATIONS_CHECK_ID),
                None,
            )
            if citations_item is None:
                continue

            total += 1
            status_key = _classify_citations_status(citations_item)
            counts[status_key] += 1
            if timestamp is not None:
                day = timestamp.date().isoformat()
                if day in buckets:
                    if status_key == "pass":
                        buckets[day]["pass"] += 1
                    elif status_key == "fail":
                        buckets[day]["fail"] += 1
                    else:
                        buckets[day]["warn"] += 1
                if status_key == "warn-mismatch":
                    if day in days[-7:]:
                        recent_warn_mismatch += 1
                    else:
                        previous_warn_mismatch += 1
            if status_key == "warn-mismatch":
                mismatched_article_ids[_derive_article_id(path, payload)] += 1

    anomaly = "insufficient_data"
    if total >= 3:
        if recent_warn_mismatch > previous_warn_mismatch:
            anomaly = "mismatch_rising"
        elif recent_warn_mismatch < previous_warn_mismatch:
            anomaly = "improving"
        else:
            anomaly = "stable"

    return {
        "checks_total": total,
        "by_status": counts,
        "top_mismatched_article_ids": [article_id for article_id, _count in mismatched_article_ids.most_common(5)],
        "trend_14d": [buckets[day] for day in days],
        "anomaly": anomaly,
    }


def _normalize_fallback_reason(text: str | None) -> str:
    lowered = (text or "").lower()
    if "rate" in lowered:
        return "rate_limit"
    if "auth" in lowered:
        return "auth"
    if "time" in lowered:
        return "timeout"
    return "other"


def collect_illustration_signals(since_days: int) -> dict[str, Any]:
    lookback_days = max(since_days, 14)
    cutoff = _since_cutoff(lookback_days)
    rows: list[dict[str, Any]] = []
    jsonl_path = LOGS_DIR / "illustrations.jsonl"
    if jsonl_path.exists():
        try:
            for line in jsonl_path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    rows.append(payload)
        except (OSError, json.JSONDecodeError):
            rows = []

    provider_distribution: Counter[str] = Counter()
    fallback_reasons: Counter[str] = Counter()
    total = 0
    fallback_count = 0
    monthly_cost_usd = 0.0

    for row in rows:
        timestamp = _parse_iso8601(str(row.get("timestamp") or ""))
        if timestamp is not None and timestamp < cutoff:
            continue

        total += 1
        provider = str(row.get("provider") or row.get("source") or "unknown")
        provider_distribution[provider] += 1

        try:
            if row.get("cost_estimate") is not None:
                monthly_cost_usd += float(row.get("cost_estimate"))
        except (TypeError, ValueError):
            pass

        chain = row.get("provider_chain") or []
        context = row.get("provider_context") or {}
        requested = str(context.get("requested_provider") or provider)
        used_fallback = (isinstance(chain, list) and len(chain) > 1) or (requested and requested != provider)
        if used_fallback:
            fallback_count += 1
            reason = _normalize_fallback_reason(
                str(context.get("failure_reason") or context.get("fallback_reason") or "other")
            )
            fallback_reasons[reason] += 1

    budget_cap = float(os.getenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "0.0") or 0.0)
    fallback_rate = round(fallback_count / total, 4) if total else 0.0
    budget_utilization = round(monthly_cost_usd / budget_cap, 4) if budget_cap > 0 else 0.0

    anomaly = "insufficient_data"
    if total >= 3:
        if budget_cap > 0 and budget_utilization >= 0.8:
            anomaly = "budget_approaching"
        elif fallback_rate > 0.2:
            anomaly = "fallback_rising"
        else:
            anomaly = "stable"

    return {
        "provider_distribution": dict(provider_distribution),
        "fallback_rate": fallback_rate,
        "monthly_cost_usd": round(monthly_cost_usd, 6),
        "budget_utilization": budget_utilization,
        "fallback_reasons": dict(fallback_reasons),
        "anomaly": anomaly,
    }


def collect_publish_monthly_signals(since_days: int) -> dict[str, Any]:
    lookback_days = max(since_days, 14)
    cutoff = _since_cutoff(lookback_days)
    recent_runs: list[dict[str, Any]] = []

    if REPORTS_DIR.exists():
        for path in sorted(REPORTS_DIR.glob("publish_state_*.json")):
            payload = _safe_read_json(path)
            if payload is None:
                continue
            timestamp = _payload_timestamp(path, payload)
            if timestamp is not None and timestamp < cutoff:
                continue
            telemetry = payload.get("telemetry") or {}
            recent_runs.append(
                {
                    "month": payload.get("month") or path.stem.replace("publish_state_", ""),
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "stages_duration_sec": {
                        key: float(value.get("duration_sec") or 0.0)
                        for key, value in telemetry.items()
                        if isinstance(value, dict)
                    },
                    "stages_cost_usd": {
                        key: value.get("cost_usd")
                        for key, value in telemetry.items()
                        if isinstance(value, dict)
                    },
                }
            )

    duration_map: dict[str, list[float]] = defaultdict(list)
    for run in recent_runs:
        for stage, duration in run["stages_duration_sec"].items():
            duration_map[stage].append(float(duration))

    bottleneck_stage = None
    if duration_map:
        bottleneck_stage = max(duration_map.items(), key=lambda item: _float_mean(item[1]) or 0.0)[0]

    stage_duration_change_7d: dict[str, str] = {}
    anomaly = "insufficient_data"
    if len(recent_runs) >= 2:
        previous_runs = recent_runs[:-1]
        latest_run = recent_runs[-1]
        worsening = False
        for stage, duration in latest_run["stages_duration_sec"].items():
            previous_values = [run["stages_duration_sec"].get(stage, 0.0) for run in previous_runs]
            previous_avg = _float_mean(previous_values)
            if previous_avg in (None, 0.0):
                stage_duration_change_7d[stage] = "n/a"
                continue
            pct = ((float(duration) - previous_avg) / previous_avg) * 100.0
            stage_duration_change_7d[stage] = _signed_percent_text(pct)
            if stage == bottleneck_stage and pct >= 15.0:
                worsening = True
        anomaly = "bottleneck_worsening" if worsening else "stable"

    return {
        "recent_runs": recent_runs,
        "bottleneck_stage": bottleneck_stage,
        "stage_duration_change_7d": stage_duration_change_7d,
        "anomaly": anomaly,
    }


def collect_failures(since_days: int = 7) -> dict[str, Any]:
    end = _utc_now()
    start = _since_cutoff(since_days)
    log_data = collect_log_failures(since_days)

    return {
        "period": {"from": start.isoformat(), "to": end.isoformat(), "days": since_days},
        "editorial_lint_failures": log_data["editorial_lint_failures"],
        "factcheck_summary": log_data["factcheck_summary"],
        "standards_failures": collect_standards_failures(since_days),
        "editor_corrections": collect_editor_corrections(since_days),
        "langfuse_anomalies": collect_langfuse_anomalies(since_days),
        "total_articles": collect_ghost_publications(since_days),
        "cache_signals": collect_cache_signals(since_days),
        "citations_signals": collect_citations_signals(since_days),
        "illustration_signals": collect_illustration_signals(since_days),
        "publish_monthly_signals": collect_publish_monthly_signals(since_days),
    }


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
    failures = collect_failures(since_days=7)
    assert "period" in failures
    assert "editorial_lint_failures" in failures
    assert "editor_corrections" in failures
    assert "standards_failures" in failures
    assert "total_articles" in failures
    assert "cache_signals" in failures
    assert "citations_signals" in failures
    assert "illustration_signals" in failures
    assert "publish_monthly_signals" in failures
    print("ok failure_collector smoke test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect failure and operational signals")
    parser.add_argument("--since-days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--out", help="Write output JSON to a file")
    parser.add_argument("--dry-run", action="store_true", help="Run smoke validation only")
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
