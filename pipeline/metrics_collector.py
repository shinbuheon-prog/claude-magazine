"""Aggregate operational metrics for Claude Magazine."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - optional in some environments
    requests = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
DRAFTS_DIR = ROOT / "drafts"
DATA_DIR = ROOT / "data"
CORRECTIONS_DB = DATA_DIR / "editor_corrections.db"

USD_TO_KRW = 1350
MODEL_PRICING_PER_MILLION = {
    "haiku": {"input": 0.8, "output": 4.0},
    "sonnet": {"input": 3.0, "output": 15.0},
    "opus": {"input": 15.0, "output": 75.0},
}
OPUS_CACHE_RATES_PER_MILLION = {
    "base_input": 15.0,
    "cache_read_input": 1.5,
}
AI_LOG_PREFIXES = {"brief", "draft", "factcheck", "channel", "rewrite"}
QUALITY_LOG_PREFIXES = {"lint", "standards", "factcheck"}
LINT_CITATIONS_CHECK_ID = "citations-cross-check"


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


def _parse_log_timestamp(path: Path, payload: dict[str, Any]) -> datetime | None:
    parsed = _parse_iso8601(str(payload.get("timestamp") or ""))
    if parsed is not None:
        return parsed

    stem = path.stem
    try:
        suffix = stem.rsplit("_", 1)[1]
        return datetime.strptime(suffix, "%Y%m%d_%H%M%S").replace(tzinfo=UTC)
    except (IndexError, ValueError):
        return None


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


def _model_family(model_name: str | None) -> str:
    text = (model_name or "").lower()
    for family in MODEL_PRICING_PER_MILLION:
        if family in text:
            return family
    return "sonnet"


def _estimate_cost_usd(model_name: str | None, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING_PER_MILLION[_model_family(model_name)]
    return round(
        (input_tokens / 1_000_000.0) * pricing["input"]
        + (output_tokens / 1_000_000.0) * pricing["output"],
        6,
    )


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _safe_read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def _list_recent_log_files(since: datetime) -> list[Path]:
    if not LOGS_DIR.exists():
        return []

    paths: list[Path] = []
    for path in LOGS_DIR.glob("*.json"):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        except OSError:
            continue
        if modified >= since:
            paths.append(path)
    return sorted(paths)


def _zero_14d_buckets(now: datetime) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    for offset in range(13, -1, -1):
        day = (now - timedelta(days=offset)).date().isoformat()
        buckets.append({"date": day, "pass": 0, "warn_missing": 0, "warn_mismatch": 0, "fail": 0, "total": 0})
    return buckets


@dataclass
class ArticleMetrics:
    article_id: str
    topic: str = ""
    category: str = "weekly_brief"
    draft_path: str = ""
    publish_status: str = "draft"
    ai_cost_usd: float = 0.0
    ai_input_tokens: int = 0
    ai_output_tokens: int = 0
    ai_time_sec: float = 0.0
    editor_time_sec: float = 0.0
    editor_time_estimated: bool = True
    lint_pass: bool | None = None
    standards_pass: bool | None = None
    factcheck_failures: int = 0
    corrections_count: int = 0
    open_rate: float | None = None
    ctr: float | None = None
    net_new_subscribers: int | None = None
    newsletter_recipient_count: int = 0
    ai_events: list[datetime] = field(default_factory=list)
    model_costs: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    model_tokens: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    lint_results: list[bool] = field(default_factory=list)

    def finalize(self) -> dict[str, Any]:
        if self.ai_events:
            self.ai_events.sort()
            self.ai_time_sec = max(
                0.0,
                (self.ai_events[-1] - self.ai_events[0]).total_seconds(),
            )

        ratio = None
        if self.editor_time_sec > 0:
            ratio = round(self.ai_time_sec / self.editor_time_sec, 2)

        model_distribution = [
            {
                "model": model,
                "cost_usd": round(cost, 6),
                "tokens": int(self.model_tokens.get(model, 0)),
            }
            for model, cost in sorted(
                self.model_costs.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        if self.lint_results and self.lint_pass is None:
            self.lint_pass = all(self.lint_results)

        return {
            "article_id": self.article_id,
            "topic": self.topic or self.article_id,
            "category": self.category,
            "draft_path": self.draft_path,
            "publish_status": self.publish_status,
            "cost_usd": round(self.ai_cost_usd, 6),
            "ai_time_sec": round(self.ai_time_sec, 2),
            "editor_time_sec": round(self.editor_time_sec, 2),
            "editor_time_estimated": self.editor_time_estimated,
            "ai_editor_ratio": ratio,
            "lint_pass": self.lint_pass,
            "standards_pass": self.standards_pass,
            "factcheck_failures": self.factcheck_failures,
            "corrections_count": self.corrections_count,
            "open_rate": self.open_rate,
            "ctr": self.ctr,
            "net_new_subscribers": self.net_new_subscribers,
            "newsletter_recipient_count": self.newsletter_recipient_count,
            "model_distribution": model_distribution,
            "input_tokens": self.ai_input_tokens,
            "output_tokens": self.ai_output_tokens,
        }


def _base_record(article_id: str) -> ArticleMetrics:
    return ArticleMetrics(article_id=article_id)


def _load_corrections() -> dict[str, int]:
    if not CORRECTIONS_DB.exists():
        return {}

    counts: dict[str, int] = {}
    try:
        with sqlite3.connect(CORRECTIONS_DB) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "corrections" in tables:
                rows = conn.execute(
                    "SELECT article_id, COUNT(*) FROM corrections GROUP BY article_id"
                ).fetchall()
                counts.update({str(article_id): int(count) for article_id, count in rows})
            elif "editor_corrections" in tables:
                rows = conn.execute(
                    "SELECT article_id, COUNT(*) FROM editor_corrections GROUP BY article_id"
                ).fetchall()
                counts.update({str(article_id): int(count) for article_id, count in rows})
    except sqlite3.Error:
        return {}
    return counts


def _ghost_reach_metrics() -> dict[str, Any]:
    unavailable = {
        "available": False,
        "source": "ghost",
        "reason": "Ghost API not configured",
        "posts_with_analytics": 0,
        "avg_open_rate": None,
        "avg_ctr": None,
        "net_new_subscribers": None,
    }

    if requests is None:
        unavailable["reason"] = "requests is unavailable"
        return unavailable

    api_url = os.getenv("GHOST_ADMIN_API_URL")
    api_key = os.getenv("GHOST_ADMIN_API_KEY")
    if not api_url or not api_key:
        return unavailable

    try:
        from pipeline.ghost_client import _headers, _request  # type: ignore
    except Exception:
        return unavailable

    try:
        response = _request("GET", "/posts/")
        posts = response.get("posts", [])
        return {
            "available": True,
            "source": "ghost",
            "reason": None,
            "posts_with_analytics": len(posts),
            "avg_open_rate": None,
            "avg_ctr": None,
            "net_new_subscribers": None,
            "sample_ids": [post.get("id") for post in posts[:5]],
            "headers_used": bool(_headers()),
        }
    except Exception as exc:
        unavailable["reason"] = type(exc).__name__
        return unavailable


def _langfuse_metrics() -> dict[str, Any]:
    try:
        from pipeline.observability import LANGFUSE_ENABLED  # type: ignore
    except Exception:
        LANGFUSE_ENABLED = False

    return {
        "available": bool(LANGFUSE_ENABLED),
        "source": "langfuse" if LANGFUSE_ENABLED else "logs",
        "cache_hit_rate": None,
        "p50_latency_sec": None,
        "p95_latency_sec": None,
        "p99_latency_sec": None,
        "retry_count": None,
    }


def _draft_file_for(article_id: str) -> Path | None:
    candidate = DRAFTS_DIR / f"draft_{article_id}.md"
    return candidate if candidate.exists() else None


def _brief_file_for(article_id: str) -> Path | None:
    candidate = DRAFTS_DIR / f"brief_{article_id}.json"
    return candidate if candidate.exists() else None


def _git_commit_times(path: Path) -> list[datetime]:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "log",
                "--follow",
                "--format=%cI",
                "--",
                str(path.relative_to(ROOT)),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return []

    if completed.returncode != 0:
        return []

    return [
        parsed
        for parsed in (_parse_iso8601(line.strip()) for line in completed.stdout.splitlines())
        if parsed is not None
    ]


def _estimate_editor_time_details(article_id: str) -> tuple[float, bool]:
    draft_file = _draft_file_for(article_id)
    brief_file = _brief_file_for(article_id)

    for candidate in [draft_file, brief_file]:
        if candidate is None:
            continue
        commit_times = _git_commit_times(candidate)
        if len(commit_times) >= 2:
            earliest = min(commit_times)
            latest = max(commit_times)
            return max(0.0, (latest - earliest).total_seconds()), False

    timestamps: list[float] = []
    for candidate in [brief_file, draft_file]:
        if candidate is None:
            continue
        try:
            timestamps.append(candidate.stat().st_mtime)
        except OSError:
            continue

    if len(timestamps) >= 2:
        return max(0.0, max(timestamps) - min(timestamps)), True
    if timestamps:
        return 0.0, True
    return 0.0, True


def estimate_editor_time(article_id: str) -> float:
    """Estimate editor working time in seconds using git history or file timestamps."""
    seconds, _estimated = _estimate_editor_time_details(article_id)
    return seconds


def _record_draft_files(records: dict[str, ArticleMetrics]) -> None:
    if not DRAFTS_DIR.exists():
        return

    for path in sorted(DRAFTS_DIR.glob("draft_*.md")):
        article_id = path.stem[len("draft_") :]
        record = records.setdefault(article_id, _base_record(article_id))
        record.draft_path = str(path.relative_to(ROOT))

    for path in sorted(DRAFTS_DIR.glob("brief_*.json")):
        article_id = path.stem[len("brief_") :]
        records.setdefault(article_id, _base_record(article_id))


def _load_log_records(
    since: datetime,
    article_filter: str | None,
    records: dict[str, ArticleMetrics],
) -> list[dict[str, Any]]:
    log_events: list[dict[str, Any]] = []
    for path in _list_recent_log_files(since):
        payload = _safe_read_json(path)
        if payload is None:
            continue

        article_id = _derive_article_id(path, payload)
        if article_filter and article_id != article_filter:
            continue

        record = records.setdefault(article_id, _base_record(article_id))
        event_type = path.stem.split("_", 1)[0]
        event_time = _parse_log_timestamp(path, payload)

        if payload.get("topic") and not record.topic:
            record.topic = str(payload["topic"])

        if event_type in AI_LOG_PREFIXES:
            input_tokens = int(payload.get("input_tokens") or 0)
            output_tokens = int(payload.get("output_tokens") or 0)
            model = str(payload.get("model") or "unknown")
            cost_usd = _estimate_cost_usd(model, input_tokens, output_tokens)
            record.ai_cost_usd += cost_usd
            record.ai_input_tokens += input_tokens
            record.ai_output_tokens += output_tokens
            record.model_costs[model] += cost_usd
            record.model_tokens[model] += input_tokens + output_tokens
            if event_time is not None:
                record.ai_events.append(event_time)

        if event_type in QUALITY_LOG_PREFIXES:
            status = str(payload.get("status") or "").lower()
            if event_type == "lint":
                if status:
                    record.lint_results.append(status == "pass")
                elif payload.get("items"):
                    record.lint_results.append(bool(payload.get("can_publish")))
            if event_type == "standards" and status:
                record.standards_pass = status == "pass"
            if event_type == "factcheck" and status == "fail":
                record.factcheck_failures += 1

        if event_type == "publish":
            record.publish_status = str(payload.get("status") or record.publish_status)
            record.newsletter_recipient_count += int(payload.get("recipient_count") or 0)

        log_events.append(
            {
                "path": path.name,
                "article_id": article_id,
                "type": event_type,
                "timestamp": event_time,
                "payload": payload,
            }
        )

    return log_events


def _collect_cache_metrics(log_events: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    factcheck_events = [event for event in log_events if event["type"] == "factcheck"]
    creation_total = sum(int(event["payload"].get("cache_creation_input_tokens") or 0) for event in factcheck_events)
    read_total = sum(int(event["payload"].get("cache_read_input_tokens") or 0) for event in factcheck_events)
    cached_runs = [
        event
        for event in factcheck_events
        if int(event["payload"].get("cache_creation_input_tokens") or 0) > 0
        or int(event["payload"].get("cache_read_input_tokens") or 0) > 0
        or bool(event["payload"].get("cache_enabled"))
    ]
    hit_denom = creation_total + read_total
    hit_rate = round(read_total / hit_denom, 4) if hit_denom else 0.0
    saved_per_million = OPUS_CACHE_RATES_PER_MILLION["base_input"] - OPUS_CACHE_RATES_PER_MILLION["cache_read_input"]
    estimated_saved_usd = round((read_total / 1_000_000.0) * saved_per_million, 6)

    buckets = _zero_14d_buckets(now)
    bucket_map = {bucket["date"]: bucket for bucket in buckets}
    for event in factcheck_events:
        timestamp = event.get("timestamp")
        if timestamp is None:
            continue
        day = timestamp.date().isoformat()
        bucket = bucket_map.get(day)
        if bucket is None:
            continue
        creation = int(event["payload"].get("cache_creation_input_tokens") or 0)
        read = int(event["payload"].get("cache_read_input_tokens") or 0)
        bucket["total"] += 1
        bucket.setdefault("cache_creation_tokens", 0)
        bucket.setdefault("cache_read_tokens", 0)
        bucket["cache_creation_tokens"] += creation
        bucket["cache_read_tokens"] += read
    for bucket in buckets:
        creation = int(bucket.pop("cache_creation_tokens", 0))
        read = int(bucket.pop("cache_read_tokens", 0))
        denom = creation + read
        bucket["hit_rate"] = round(read / denom, 4) if denom else 0.0

    other_pipelines = []
    for event_type, label in (("brief", "brief_generator"), ("draft", "draft_writer"), ("lint", "editorial_lint")):
        events = [event for event in log_events if event["type"] == event_type]
        other_pipelines.append(
            {
                "pipeline": label,
                "runs": len(events),
                "cache_enabled_runs": sum(1 for event in events if bool(event["payload"].get("cache_enabled"))),
            }
        )

    return {
        "fact_checker": {
            "runs": len(factcheck_events),
            "runs_with_cache_enabled": len(cached_runs),
            "total_cache_creation_tokens": creation_total,
            "total_cache_read_tokens": read_total,
            "cache_hit_rate": hit_rate,
            "estimated_saved_usd": estimated_saved_usd,
            "trend_14d": buckets,
        },
        "other_pipelines": other_pipelines,
    }


def _classify_citations_item(item: dict[str, Any]) -> str:
    status = str(item.get("status") or "").lower()
    message = str(item.get("message") or "").lower()
    if status == "pass":
        return "pass"
    if status == "fail":
        return "fail"
    if "no citations data" in message:
        return "warn_missing"
    if "not backed" in message or "manual source_id" in message:
        return "warn_mismatch"
    return "warn_missing"


def _collect_citations_metrics(log_events: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    lint_events = [event for event in log_events if event["type"] == "lint" and event["payload"].get("mode") == "article"]
    relevant_items: list[tuple[datetime | None, str]] = []
    for event in lint_events:
        items = event["payload"].get("items") or []
        citations_item = next((item for item in items if item.get("id") == LINT_CITATIONS_CHECK_ID), None)
        if citations_item is None:
            continue
        relevant_items.append((event.get("timestamp"), _classify_citations_item(citations_item)))

    counts = {"pass": 0, "warn_missing": 0, "warn_mismatch": 0, "fail": 0}
    buckets = _zero_14d_buckets(now)
    bucket_map = {bucket["date"]: bucket for bucket in buckets}
    for timestamp, bucket_key in relevant_items:
        counts[bucket_key] += 1
        if timestamp is None:
            continue
        day = timestamp.date().isoformat()
        bucket = bucket_map.get(day)
        if bucket is None:
            continue
        bucket[bucket_key] += 1
        bucket["total"] += 1

    total = len(relevant_items)
    pass_rate = round(counts["pass"] / total, 4) if total else None
    return {
        "article_runs_with_citations_check": total,
        "pass": counts["pass"],
        "warn_missing": counts["warn_missing"],
        "warn_mismatch": counts["warn_mismatch"],
        "fail": counts["fail"],
        "pass_rate": pass_rate,
        "trend_14d": buckets,
    }


def _collect_illustration_metrics(since: datetime) -> dict[str, Any]:
    log_path = LOGS_DIR / "illustrations.jsonl"
    rows = _safe_read_jsonl(log_path)
    provider_distribution: dict[str, int] = defaultdict(int)
    monthly_cost_by_provider: dict[str, float] = defaultdict(float)
    monthly_cost_usd = 0.0

    for row in rows:
        timestamp = _parse_iso8601(str(row.get("timestamp") or ""))
        if timestamp is not None and timestamp < since:
            continue
        provider = str(row.get("provider") or row.get("source") or "unknown")
        provider_distribution[provider] += 1
        cost = row.get("cost_estimate")
        if cost is None:
            continue
        try:
            cost_value = float(cost)
        except (TypeError, ValueError):
            continue
        monthly_cost_usd += cost_value
        monthly_cost_by_provider[provider] += cost_value

    budget_cap_usd = float(os.getenv("CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP", "5") or 5.0)
    utilization = round(monthly_cost_usd / budget_cap_usd, 4) if budget_cap_usd > 0 else None
    return {
        "provider_distribution": dict(sorted(provider_distribution.items())),
        "monthly_cost_usd": round(monthly_cost_usd, 6),
        "monthly_cost_by_provider": {
            provider: round(cost, 6) for provider, cost in sorted(monthly_cost_by_provider.items())
        },
        "budget_cap_usd": round(budget_cap_usd, 2),
        "budget_utilization": utilization,
    }


def _operations_summary(log_events: list[dict[str, Any]]) -> dict[str, Any]:
    publish_events = [event for event in log_events if event["type"] == "publish"]
    publish_successes = sum(
        1
        for event in publish_events
        if str(event["payload"].get("status") or "").lower() in {"published", "draft"}
    )
    publish_failures = sum(
        1
        for event in publish_events
        if str(event["payload"].get("status") or "").lower() == "failed"
    )

    publish_monthly = {
        "last_month": None,
        "stages_duration_sec": {},
        "stages_cost_usd": {},
    }
    state_files = sorted((ROOT / "reports").glob("publish_state_*.json"))
    if state_files:
        latest = state_files[-1]
        payload = _safe_read_json(latest) or {}
        telemetry = payload.get("telemetry") or {}
        publish_monthly = {
            "last_month": payload.get("month"),
            "stages_duration_sec": {
                key: value.get("duration_sec")
                for key, value in telemetry.items()
                if isinstance(value, dict)
            },
            "stages_cost_usd": {
                key: value.get("cost_usd")
                for key, value in telemetry.items()
                if isinstance(value, dict)
            },
        }

    return {
        "publish_runs": len(publish_events),
        "publish_successes": publish_successes,
        "publish_failures": publish_failures,
        "n8n_execution_rate": None,
        "alert_failures": 0,
        "asset_upload_failures": 0,
        "sns_publish_failures": 0,
        "publish_monthly": publish_monthly,
        "available": {
            "publish_logs": True,
            "n8n": False,
            "sns_assets": False,
        },
    }


def collect_metrics(
    since_days: int = 30,
    article_id: str | None = None,
) -> dict[str, Any]:
    """
    Aggregate metrics across logs, drafts, optional databases, and external systems.
    """
    now = datetime.now(UTC)
    since = now - timedelta(days=since_days)
    records: dict[str, ArticleMetrics] = {}

    _record_draft_files(records)
    log_events = _load_log_records(since, article_id, records)

    corrections = _load_corrections()
    for key, count in corrections.items():
        if article_id and key != article_id:
            continue
        record = records.setdefault(key, _base_record(key))
        record.corrections_count = count

    finalized: list[dict[str, Any]] = []
    for key, record in sorted(records.items()):
        if article_id and key != article_id:
            continue
        editor_time_sec, estimated = _estimate_editor_time_details(key)
        record.editor_time_sec = editor_time_sec
        record.editor_time_estimated = estimated
        finalized.append(record.finalize())

    finalized = [
        item
        for item in finalized
        if item["cost_usd"] > 0
        or item["draft_path"]
        or item["publish_status"] != "draft"
        or not article_id
    ]

    total_cost_usd = round(sum(item["cost_usd"] for item in finalized), 6)
    total_ai_time_sec = round(sum(item["ai_time_sec"] for item in finalized), 2)
    total_editor_time_sec = round(sum(item["editor_time_sec"] for item in finalized), 2)
    article_count = len(finalized)
    avg_cost_usd = round(total_cost_usd / article_count, 6) if article_count else 0.0
    ai_human_ratio = (
        round(total_ai_time_sec / total_editor_time_sec, 2)
        if total_editor_time_sec > 0
        else None
    )

    model_distribution: dict[str, float] = defaultdict(float)
    for item in finalized:
        for model_entry in item["model_distribution"]:
            model_distribution[model_entry["model"]] += float(model_entry["cost_usd"])

    quality_known = [item for item in finalized if item["lint_pass"] is not None]
    lint_pass_count = sum(1 for item in quality_known if item["lint_pass"])
    lint_pass_rate = round(lint_pass_count / len(quality_known), 2) if quality_known else None

    reach_external = _ghost_reach_metrics()
    langfuse_metrics = _langfuse_metrics()
    operations = _operations_summary(log_events)
    cache_metrics = _collect_cache_metrics(log_events, now)
    citations_metrics = _collect_citations_metrics(log_events, now)
    illustration_metrics = _collect_illustration_metrics(since)

    return {
        "generated_at": now.isoformat(),
        "period": {
            "from": since.isoformat(),
            "to": now.isoformat(),
            "days": since_days,
        },
        "sources": {
            "logs": LOGS_DIR.exists(),
            "drafts": DRAFTS_DIR.exists(),
            "editor_corrections_db": CORRECTIONS_DB.exists(),
            "ghost": reach_external["available"],
            "langfuse": langfuse_metrics["available"],
        },
        "cost": {
            "total_usd": total_cost_usd,
            "total_krw": round(total_cost_usd * USD_TO_KRW),
            "per_article_usd": avg_cost_usd,
            "article_count": article_count,
            "estimated": True,
            "model_distribution": [
                {"model": model, "cost_usd": round(cost, 6)}
                for model, cost in sorted(
                    model_distribution.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
        },
        "time": {
            "ai_total_sec": total_ai_time_sec,
            "editor_total_sec": total_editor_time_sec,
            "ai_editor_ratio": ai_human_ratio,
            "editor_time_estimated": any(item["editor_time_estimated"] for item in finalized),
            "article_lead_time_sec": total_ai_time_sec + total_editor_time_sec,
            "langfuse": langfuse_metrics,
        },
        "quality": {
            "lint_pass_rate": lint_pass_rate,
            "lint_checked_articles": len(quality_known),
            "lint_pass_count": lint_pass_count,
            "factcheck_failures": sum(item["factcheck_failures"] for item in finalized),
            "corrections_total": sum(item["corrections_count"] for item in finalized),
            "available": {
                "lint": bool(quality_known),
                "standards": any(item["standards_pass"] is not None for item in finalized),
                "corrections_db": CORRECTIONS_DB.exists(),
            },
        },
        "reach": {
            "published_articles": sum(
                1 for item in finalized if item["publish_status"] == "published"
            ),
            "newsletter_recipients": sum(
                item["newsletter_recipient_count"] for item in finalized
            ),
            "avg_open_rate": reach_external["avg_open_rate"],
            "avg_ctr": reach_external["avg_ctr"],
            "net_new_subscribers": reach_external["net_new_subscribers"],
            "available": {
                "ghost": reach_external["available"],
                "local_publish_logs": True,
            },
            "ghost": reach_external,
        },
        "operations": operations,
        "cache": cache_metrics,
        "citations": citations_metrics,
        "illustration": illustration_metrics,
        "per_article": finalized,
    }
