"""
Source diversity rules engine.

Usage:
    python pipeline/source_diversity.py --article-id art-001
    python pipeline/source_diversity.py --sources src1.md src2.md --strict
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

try:
    from pipeline.source_registry import list_sources
except ModuleNotFoundError:
    from source_registry import list_sources  # type: ignore

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
RECENT_DAYS = 30
BACKGROUND_DAYS = 365
PUBLISHER_CONCENTRATION_LIMIT = 0.60
STANCE_VALUES = {"pro", "neutral", "con", "unknown", "affected"}
RULE_ORDER = ["language", "stance", "publisher", "recency", "triple_pattern"]
RULE_LABELS = {
    "language": "Language Diversity",
    "stance": "Stance Diversity",
    "publisher": "Publisher Concentration",
    "recency": "Recency Balance",
    "triple_pattern": "Triple Pattern",
}


def classify_stance(source_text: str, topic: str) -> str:
    if not (source_text or "").strip():
        return "unknown"

    kind = (os.environ.get("CLAUDE_PROVIDER", "api")).lower()
    if kind == "api" and not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "unknown"

    try:
        try:
            from pipeline.claude_provider import get_provider
        except ModuleNotFoundError:
            from claude_provider import get_provider  # type: ignore

        provider = get_provider()
        system_prompt = (
            "You classify the stance of a source toward a topic.\n"
            "Return exactly one token: pro, neutral, con, affected, or unknown.\n"
            "'affected' means the source primarily reflects impacted users, customers, or operators.\n"
            "If unsure, return unknown."
        )
        preview = source_text[:8000]
        user_prompt = f"Topic: {topic or '(unknown)'}\n\n--- Source ---\n{preview}"
        result = provider.stream_complete(
            system=system_prompt,
            user=user_prompt,
            model_tier="haiku",
            max_tokens=16,
        )
        _write_classify_log(topic, result.request_id, result.text)
        token = result.text.strip().lower().split()[0] if result.text.strip() else ""
        token = token.strip(".,;:\"'`")
        return token if token in STANCE_VALUES else "unknown"
    except Exception:
        return "unknown"


def _write_classify_log(topic: str, request_id: str | None, raw: str) -> None:
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "model": HAIKU_MODEL,
            "topic": topic,
            "raw_response": (raw or "")[:256],
        }
        path = LOGS_DIR / f"stance_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _parse_source_file(path: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "source_id": f"file:{path.name}",
        "url": str(path),
        "publisher": path.stem,
        "language": "unknown",
        "stance": "neutral",
        "is_official": 0,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return meta

    if text.startswith("---"):
        end_idx = text.find("\n---", 3)
        if end_idx > 0:
            header = text[3:end_idx].strip()
            for line in header.splitlines():
                if ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key in {"url", "publisher", "language", "stance", "retrieved_at"}:
                    meta[key] = val
                elif key == "is_official":
                    try:
                        meta["is_official"] = int(val)
                    except ValueError:
                        meta["is_official"] = 0
    return meta


def _parse_retrieved_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _rule_language(sources: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    ko_official = [s for s in sources if s.get("language") == "ko" and int(s.get("is_official") or 0) == 1]
    en_official = [s for s in sources if s.get("language") == "en" and int(s.get("is_official") or 0) == 1]
    recommendations: list[str] = []
    if not ko_official:
        recommendations.append("Add at least one Korean official source.")
    if not en_official:
        recommendations.append("Add at least one English official source.")
    detail = f"ko official={len(ko_official)}, en official={len(en_official)}"
    return {"id": "language", "status": "pass" if ko_official and en_official else "fail", "detail": detail}, recommendations


def _rule_stance(sources: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    counts = Counter((s.get("stance") or "unknown") for s in sources)
    categories = {key for key in counts if key in {"pro", "neutral", "con", "affected"} and counts[key] > 0}
    detail = ", ".join(f"{key}={counts.get(key, 0)}" for key in ("pro", "neutral", "con", "affected", "unknown"))
    if len(categories) >= 2:
        return {"id": "stance", "status": "pass", "detail": detail}, []

    recommendations: list[str] = []
    if "con" not in categories and "affected" not in categories:
        recommendations.append("Add at least one opposing or affected source.")
    if "pro" not in categories and "neutral" not in categories:
        recommendations.append("Add at least one pro or neutral source.")
    return {"id": "stance", "status": "fail", "detail": detail}, recommendations


def _rule_publisher(sources: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    total = len(sources)
    if total == 0:
        return {"id": "publisher", "status": "fail", "detail": "No sources registered."}, ["Register at least two sources."]
    counts = Counter((s.get("publisher") or "?") for s in sources)
    top_pub, top_count = counts.most_common(1)[0]
    ratio = top_count / total
    detail = f"top publisher={top_pub} ({top_count}/{total}, {ratio:.0%})"
    if ratio <= PUBLISHER_CONCENTRATION_LIMIT:
        return {"id": "publisher", "status": "pass", "detail": detail}, []
    return (
        {"id": "publisher", "status": "fail", "detail": detail},
        [f"Add more non-{top_pub} sources to keep concentration under {int(PUBLISHER_CONCENTRATION_LIMIT * 100)}%."],
    )


def _rule_recency(sources: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    now = datetime.now(timezone.utc)
    recent = 0
    background = 0
    for source in sources:
        dt = _parse_retrieved_at(source.get("retrieved_at"))
        if dt is None:
            continue
        age = now - dt
        if age <= timedelta(days=RECENT_DAYS):
            recent += 1
        if age >= timedelta(days=BACKGROUND_DAYS):
            background += 1
    detail = f"recent_30d={recent}, background_365d={background}"
    recommendations: list[str] = []
    if recent == 0:
        recommendations.append("Add at least one source from the last 30 days.")
    if background == 0:
        recommendations.append("Add at least one background source older than 365 days.")
    return {"id": "recency", "status": "pass" if recent and background else "fail", "detail": detail}, recommendations


def check_triple_pattern(article_sources: list[dict[str, Any]], *, editor_approved_exception: bool = False) -> dict[str, Any]:
    ko_official = [s for s in article_sources if s.get("language") == "ko" and int(s.get("is_official") or 0) == 1]
    en_official = [s for s in article_sources if s.get("language") == "en" and int(s.get("is_official") or 0) == 1]
    opposing = [s for s in article_sources if (s.get("stance") or "unknown") in {"con", "affected"}]
    missing: list[str] = []
    if not ko_official:
        missing.append("korean_official")
    if not en_official:
        missing.append("source_official")
    if not opposing:
        missing.append("opposing_or_affected")

    passed = not missing or bool(editor_approved_exception)
    recommendation = "pass" if not missing else f"Add sources for: {', '.join(missing)}"
    if editor_approved_exception and missing:
        recommendation = f"editor-approved exception: {recommendation}"

    return {
        "id": "triple_pattern",
        "status": "pass" if passed else "fail",
        "detail": recommendation,
        "details": {
            "korean_official_count": len(ko_official),
            "source_official_count": len(en_official),
            "opposing_or_affected_count": len(opposing),
            "missing_categories": missing,
            "editor_approved_exception": bool(editor_approved_exception),
        },
        "recommendation": recommendation,
    }


def _check_sources(sources: list[dict[str, Any]], *, editor_approved_exception: bool = False) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    recommendations: list[str] = []

    for fn in (_rule_language, _rule_stance, _rule_publisher, _rule_recency):
        rule, recs = fn(sources)
        rules.append(rule)
        recommendations.extend(recs)

    triple = check_triple_pattern(sources, editor_approved_exception=editor_approved_exception)
    rules.append(triple)
    if triple["status"] != "pass":
        recommendations.append(triple["recommendation"])

    seen: set[str] = set()
    unique_recs = []
    for rec in recommendations:
        if rec and rec not in seen:
            seen.add(rec)
            unique_recs.append(rec)

    failed = [rule["id"] for rule in rules if rule["status"] != "pass"]
    return {
        "passed": len(failed) == 0,
        "all_passed": len(failed) == 0,
        "rules": rules,
        "summary": "all rules passed" if not failed else f"{len(failed)} rule(s) failed",
        "critical_missing": failed,
        "recommendation": "Proceed" if not failed else "Add missing source coverage before publish.",
        "recommendations": unique_recs,
    }


def check_diversity(article_id: str, strict: bool = True, *, editor_approved_exception: bool = False) -> dict[str, Any]:
    sources = list_sources(article_id)
    result = _check_sources(sources, editor_approved_exception=editor_approved_exception)
    result["article_id"] = article_id
    result["strict"] = strict
    return result


def check_diversity_from_files(paths: Iterable[str], *, editor_approved_exception: bool = False) -> dict[str, Any]:
    sources = [_parse_source_file(Path(path)) for path in paths]
    return _check_sources(sources, editor_approved_exception=editor_approved_exception)


def _format_report(result: dict[str, Any], header: str, total: int) -> str:
    lines = ["=== Source Diversity Check ===", header, f"Total sources: {total}", ""]
    rule_map = {rule["id"]: rule for rule in result["rules"]}
    for idx, rule_id in enumerate(RULE_ORDER, start=1):
        rule = rule_map.get(rule_id, {"status": "fail", "detail": "(missing)"})
        icon = "PASS" if rule["status"] == "pass" else "WARN"
        lines.append(f"[{idx}/{len(RULE_ORDER)}] {RULE_LABELS[rule_id]}")
        lines.append(f"  {icon} {rule['detail']}")
        if rule_id == "triple_pattern" and rule.get("details"):
            details = rule["details"]
            lines.append(
                "  counts: "
                f"ko={details.get('korean_official_count', 0)}, "
                f"en={details.get('source_official_count', 0)}, "
                f"opp/affected={details.get('opposing_or_affected_count', 0)}"
            )
        lines.append("")
    passed_count = sum(1 for rule in result["rules"] if rule["status"] == "pass")
    lines.append(f"=== Result: {passed_count} passed / {len(result['rules']) - passed_count} warnings ===")
    if result.get("recommendations"):
        lines.append("Recommendations:")
        for rec in result["recommendations"]:
            lines.append(f"  - {rec}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Source diversity rules engine")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--article-id", dest="article_id", help="source_registry article id")
    group.add_argument("--sources", nargs="+", help="source file paths")
    parser.add_argument("--strict", action="store_true", help="return exit 1 when any rule fails")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    parser.add_argument("--dry-run", action="store_true", help="evaluate locally without side effects")
    parser.add_argument(
        "--editor-approved-exception",
        action="store_true",
        help="allow manual exception for the triple pattern rule",
    )
    args = parser.parse_args()

    if args.article_id:
        sources = list_sources(args.article_id)
        result = _check_sources(sources, editor_approved_exception=args.editor_approved_exception)
        header = f"article_id: {args.article_id}"
    else:
        sources = [_parse_source_file(Path(path)) for path in args.sources]
        result = _check_sources(sources, editor_approved_exception=args.editor_approved_exception)
        header = f"sources: {len(args.sources)} file(s)"

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_report(result, header, len(sources)))

    if args.strict and not result["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
