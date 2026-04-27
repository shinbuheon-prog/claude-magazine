from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "source_registry.db"
LOGS_DIR = ROOT / "logs"
REPORTS_DIR = ROOT / "reports"
STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "your", "about", "have",
    "been", "will", "what", "when", "where", "how", "why", "using",
    "agent", "news", "reddit", "hackernews",
}


def _get_provider():
    from pipeline.claude_provider import get_provider

    return get_provider()


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS]


def _append_log(payload: dict[str, Any], month: str) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGS_DIR / f"monthly_curator_{month}.json"
    entries: list[dict[str, Any]] = []
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                entries = loaded
        except Exception:
            entries = []
    entries.append(payload)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _fetch_sources(month: str, feed_filter: list[str] | None = None) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM sources WHERE substr(retrieved_at, 1, 7) = ? ORDER BY retrieved_at ASC",
            (month,),
        ).fetchall()
    finally:
        conn.close()
    results = []
    for row in rows:
        item = dict(row)
        item["topics"] = json.loads(item.get("topics") or "[]")
        item["key_quotes"] = json.loads(item.get("key_quotes") or "[]")
        if feed_filter and item.get("source_type") not in feed_filter:
            continue
        results.append(item)
    return results


def _build_tfidf_candidates(sources: list[dict[str, Any]], min_cluster_size: int) -> list[dict[str, Any]]:
    token_to_sources: dict[str, set[str]] = defaultdict(set)
    pair_counter: Counter[tuple[str, str]] = Counter()
    source_tokens: dict[str, list[str]] = {}
    for source in sources:
        text = " ".join(
            [
                str(source.get("title") or ""),
                str(source.get("summary_oneliner") or ""),
                " ".join(source.get("topics") or []),
            ]
        )
        tokens = sorted(set(_tokenize(text)))
        source_tokens[source["source_id"]] = tokens
        for token in tokens:
            token_to_sources[token].add(source["source_id"])
        for idx, left in enumerate(tokens):
            for right in tokens[idx + 1 :]:
                pair_counter[(left, right)] += 1

    candidates: list[dict[str, Any]] = []
    for (left, right), count in pair_counter.most_common(20):
        members = sorted(
            source_id for source_id, tokens in source_tokens.items() if left in tokens and right in tokens
        )
        if len(members) < min_cluster_size:
            continue
        candidates.append(
            {
                "pair": [left, right],
                "pair_count": count,
                "source_ids": members,
            }
        )
    return candidates[:10]


def _cluster_payload_from_candidates(candidates: list[dict[str, Any]], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_map = {source["source_id"]: source for source in sources}
    clusters: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates, start=1):
        source_ids = candidate["source_ids"]
        days = sorted({str(source_map[sid]["retrieved_at"])[:10] for sid in source_ids if sid in source_map})
        pair = "-".join(candidate["pair"])
        clusters.append(
            {
                "cluster_id": f"{pair}-{idx}",
                "days_covered": days,
                "source_ids": source_ids,
                "proposed_angle": f"{candidate['pair'][0]} x {candidate['pair'][1]} trend",
                "magazine_section_candidate": "insight",
                "target_pages": 3,
                "priority_score": round(len(source_ids) + candidate["pair_count"] / 10, 2),
            }
        )
    return clusters


def _call_cluster_llm(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    provider = _get_provider()
    prompt = (
        "TF-IDF candidate clusters:\n"
        f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        "Return JSON {\"clusters\": [...]} with merged clusters for a magazine issue."
    )
    result = provider.stream_complete(
        system="You are a monthly editorial curator. Return JSON only.",
        user=prompt,
        model_tier="opus",
        max_tokens=1200,
    )
    match = re.search(r"\{[\s\S]*\}", result.text or "")
    parsed = json.loads(match.group(0)) if match else {"clusters": []}
    clusters = parsed.get("clusters") if isinstance(parsed, dict) else []
    if not isinstance(clusters, list):
        clusters = []
    meta = {
        "request_id": result.request_id,
        "model": result.model,
        "provider": result.provider,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
    return clusters, meta


def _call_gap_llm(clusters: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    provider = _get_provider()
    prompt = (
        "Magazine sections: cover, feature, deep_dive, insight, interview, review, sponsored.\n"
        f"Clusters:\n{json.dumps(clusters, ensure_ascii=False, indent=2)}\n\n"
        "Write a short gap analysis and propose missing briefs."
    )
    result = provider.stream_complete(
        system="You are a monthly editorial planner.",
        user=prompt,
        model_tier="opus",
        max_tokens=900,
    )
    meta = {
        "request_id": result.request_id,
        "model": result.model,
        "provider": result.provider,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
    return result.text.strip(), meta


def _render_markdown(month: str, clusters: list[dict[str, Any]], gap_analysis: str, source_count: int) -> str:
    lines = [
        f"# Monthly External Digest {month}",
        "",
        "## editor_approval",
        "",
        "```yaml",
        "status: proposed",
        "reviewer: pending",
        f"reviewed_at: {datetime.now(timezone.utc).isoformat()}",
        "notes: |",
        "  - Gate 1 review pending.",
        "```",
        "",
        "## 0. Source Summary",
        "",
        f"- source_count: {source_count}",
        f"- cluster_count: {len(clusters)}",
        "",
        "## 1. Topic Clusters",
        "",
    ]
    if clusters:
        for cluster in clusters:
            lines.extend(
                [
                    f"### {cluster['cluster_id']}",
                    f"- angle: {cluster.get('proposed_angle', '')}",
                    f"- section: {cluster.get('magazine_section_candidate', '')}",
                    f"- days_covered: {', '.join(cluster.get('days_covered', []))}",
                    f"- source_ids: {', '.join(cluster.get('source_ids', []))}",
                    "",
                ]
            )
    else:
        lines.append("- no clusters detected")
        lines.append("")

    lines.extend(
        [
            "## 2. Magazine Section Mapping",
            "",
            "| cluster_id | section | target_pages | priority_score |",
            "|---|---|---:|---:|",
        ]
    )
    for cluster in clusters:
        lines.append(
            f"| {cluster['cluster_id']} | {cluster.get('magazine_section_candidate', '')} | "
            f"{cluster.get('target_pages', 0)} | {cluster.get('priority_score', 0)} |"
        )
    lines.extend(
        [
            "",
            "## 3. Gap Analysis",
            "",
            gap_analysis or "- no gap analysis",
            "",
            "## 4. Gate 2 Preflight",
            "",
            "1. Verify source_registry metadata and quote limits.",
            "2. Confirm request_id logs exist for LLM-assisted steps.",
            "3. Review section mapping before plan_issue registration.",
            "",
            "## 5. AI Usage Disclosure",
            "",
            "This digest was assembled with TF-IDF heuristics and Claude-assisted editorial clustering.",
            "",
        ]
    )
    return "\n".join(lines)


def curate_monthly_external(
    month: str,
    feed_filter: list[str] | None = None,
    min_cluster_size: int = 2,
    output_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    sources = _fetch_sources(month, feed_filter=feed_filter)
    candidates = _build_tfidf_candidates(sources, min_cluster_size=min_cluster_size)
    fallback_clusters = _cluster_payload_from_candidates(candidates, sources)
    request_ids: list[str | None] = []

    if dry_run:
        clusters = fallback_clusters
        gap_analysis = "dry-run: TF-IDF candidate clusters only; no LLM clustering executed."
    else:
        clusters, cluster_meta = _call_cluster_llm(candidates)
        request_ids.append(cluster_meta["request_id"])
        if not clusters:
            clusters = fallback_clusters
        gap_analysis, gap_meta = _call_gap_llm(clusters)
        request_ids.append(gap_meta["request_id"])
        _append_log({"stage": "cluster", **cluster_meta}, month)
        _append_log({"stage": "gap", **gap_meta}, month)

    report_path = Path(output_path) if output_path else REPORTS_DIR / f"monthly_external_digest_{month}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = _render_markdown(month, clusters, gap_analysis, len(sources))
    report_path.write_text(markdown, encoding="utf-8")
    return {
        "clusters": clusters,
        "gap_analysis": gap_analysis,
        "source_count": len(sources),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "output_path": str(report_path),
        "request_ids": request_ids,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Curate monthly external sources")
    parser.add_argument("--month", required=True)
    parser.add_argument("--feed")
    parser.add_argument("--min-cluster-size", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    feed_filter = [item.strip() for item in (args.feed or "").split(",") if item.strip()] or None
    payload = curate_monthly_external(
        month=args.month,
        feed_filter=feed_filter,
        min_cluster_size=args.min_cluster_size,
        output_path=args.output,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
