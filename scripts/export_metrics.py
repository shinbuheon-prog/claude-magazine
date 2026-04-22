"""Export operational metrics in JSON, CSV, or Markdown formats."""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

try:
    from pipeline.metrics_collector import collect_metrics
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline.metrics_collector import collect_metrics


def _json_output(metrics: dict[str, Any]) -> str:
    return json.dumps(metrics, ensure_ascii=False, indent=2)


def _csv_output(metrics: dict[str, Any], per_article: bool) -> str:
    buffer = io.StringIO()
    if per_article:
        rows = metrics.get("per_article", [])
        fieldnames = [
            "article_id",
            "topic",
            "category",
            "publish_status",
            "cost_usd",
            "ai_time_sec",
            "editor_time_sec",
            "editor_time_estimated",
            "ai_editor_ratio",
            "lint_pass",
            "standards_pass",
            "factcheck_failures",
            "corrections_count",
            "open_rate",
            "ctr",
            "net_new_subscribers",
            "newsletter_recipient_count",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
        return buffer.getvalue()

    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "period_days",
            "article_count",
            "total_cost_usd",
            "cost_per_article_usd",
            "ai_total_sec",
            "editor_total_sec",
            "ai_editor_ratio",
            "lint_pass_rate",
            "published_articles",
            "newsletter_recipients",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "period_days": metrics["period"]["days"],
            "article_count": metrics["cost"]["article_count"],
            "total_cost_usd": metrics["cost"]["total_usd"],
            "cost_per_article_usd": metrics["cost"]["per_article_usd"],
            "ai_total_sec": metrics["time"]["ai_total_sec"],
            "editor_total_sec": metrics["time"]["editor_total_sec"],
            "ai_editor_ratio": metrics["time"]["ai_editor_ratio"],
            "lint_pass_rate": metrics["quality"]["lint_pass_rate"],
            "published_articles": metrics["reach"]["published_articles"],
            "newsletter_recipients": metrics["reach"]["newsletter_recipients"],
        }
    )
    return buffer.getvalue()


def _fmt_seconds(value: float | int | None) -> str:
    if not value:
        return "0m"
    minutes = round(float(value) / 60.0, 1)
    return f"{minutes}m"


def _markdown_output(metrics: dict[str, Any]) -> str:
    cost = metrics["cost"]
    time = metrics["time"]
    quality = metrics["quality"]
    reach = metrics["reach"]
    operations = metrics["operations"]

    lines = [
        f"# Claude Magazine Metrics ({metrics['period']['days']}d)",
        "",
        f"- Generated: {metrics['generated_at']}",
        f"- Articles: {cost['article_count']}",
        f"- Total API cost: ${cost['total_usd']:.4f}",
        f"- Cost per article: ${cost['per_article_usd']:.4f}",
        f"- AI : editor ratio: {time['ai_editor_ratio'] if time['ai_editor_ratio'] is not None else 'n/a'}",
        f"- AI time: {_fmt_seconds(time['ai_total_sec'])}",
        f"- Editor time: {_fmt_seconds(time['editor_total_sec'])}",
        "",
        "## Quality",
        "",
        f"- Lint pass rate: {quality['lint_pass_rate'] if quality['lint_pass_rate'] is not None else 'n/a'}",
        f"- Factcheck failures: {quality['factcheck_failures']}",
        f"- Corrections: {quality['corrections_total']}",
        "",
        "## Reach",
        "",
        f"- Published articles: {reach['published_articles']}",
        f"- Newsletter recipients: {reach['newsletter_recipients']}",
        f"- Ghost analytics available: {reach['available']['ghost']}",
        "",
        "## Operations",
        "",
        f"- Publish runs: {operations['publish_runs']}",
        f"- Publish failures: {operations['publish_failures']}",
        "",
        "## Per Article",
        "",
        "| Article | Cost (USD) | AI Time | Editor Time | Ratio | Publish |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for item in metrics.get("per_article", []):
        lines.append(
            "| {article} | ${cost:.4f} | {ai} | {editor} | {ratio} | {status} |".format(
                article=item["topic"],
                cost=item["cost_usd"],
                ai=_fmt_seconds(item["ai_time_sec"]),
                editor=_fmt_seconds(item["editor_time_sec"]),
                ratio=item["ai_editor_ratio"] if item["ai_editor_ratio"] is not None else "n/a",
                status=item["publish_status"],
            )
        )

    return "\n".join(lines) + "\n"


def _write_or_print(text: str, output: Path | None) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote {output}")
        return
    sys.stdout.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Claude Magazine metrics")
    parser.add_argument("--since-days", type=int, default=30, help="Lookback window")
    parser.add_argument("--article-id", help="Collect only one article")
    parser.add_argument(
        "--format",
        choices=("json", "csv", "md"),
        default="json",
        help="Export format",
    )
    parser.add_argument("--per-article", action="store_true", help="CSV per article rows")
    parser.add_argument("--output", type=Path, help="Output file path")
    args = parser.parse_args()

    metrics = collect_metrics(since_days=args.since_days, article_id=args.article_id)

    if args.format == "json":
        text = _json_output(metrics)
    elif args.format == "csv":
        text = _csv_output(metrics, per_article=args.per_article)
    else:
        text = _markdown_output(metrics)

    _write_or_print(text, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
