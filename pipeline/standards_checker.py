from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ID_PATTERN = re.compile(r"\[src-[A-Za-z0-9_-]+\]|\(source_id:\s*[^)]+\)")
WORD_RE = re.compile(r"[A-Za-z0-9가-힣]+")
QUOTE_RE = re.compile(r'"([^"\n]{2,200})"|“([^”\n]{2,200})”')
NUMBER_RE = re.compile(r"\d[\d,\.]*\s?(?:%|건|명|개|배|원|달러|MTok)?")
HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+)$", re.MULTILINE)


def load_standards(path: str = "spec/article_standards.yml") -> dict:
    full_path = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not full_path.exists():
        raise FileNotFoundError(f"standards file not found: {full_path}")
    data = yaml.safe_load(full_path.read_text(encoding="utf-8"))
    _validate_schema(data)
    return data


def _validate_schema(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("root must be a mapping")
    common = data.get("common")
    categories = data.get("categories")
    if not isinstance(common, dict):
        raise ValueError("common must be a mapping")
    if not isinstance(categories, dict) or not categories:
        raise ValueError("categories must be a non-empty mapping")
    _validate_rule_list(common.get("must_pass"), "common.must_pass")
    for category, spec in categories.items():
        if not isinstance(spec, dict):
            raise ValueError(f"categories.{category} must be a mapping")
        _validate_rule_list(spec.get("must_pass"), f"categories.{category}.must_pass")
        should_pass = spec.get("should_pass", [])
        if should_pass is not None:
            _validate_rule_list(should_pass, f"categories.{category}.should_pass")


def _validate_rule_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{idx}] must be a mapping")
        if not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError(f"{label}[{idx}].id must be a non-empty string")
        if not isinstance(item.get("rule"), str) or not item["rule"]:
            raise ValueError(f"{label}[{idx}].rule must be a non-empty string")
        if not isinstance(item.get("measure"), str) or not item["measure"]:
            raise ValueError(f"{label}[{idx}].measure must be a non-empty string")


def _split_sentences(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sentences: list[str] = []
    for line in lines:
        if line.startswith(("#", "-", "*", ">", "|", "```")):
            continue
        for part in re.split(r"(?<=[.!?。！？])\s+|\n+", line):
            part = part.strip()
            if len(part) >= 8:
                sentences.append(part)
    return sentences


def _count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def _extract_quotes(text: str) -> list[str]:
    quotes: list[str] = []
    for a, b in QUOTE_RE.findall(text):
        quotes.append(a or b)
    return quotes


def _source_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if SOURCE_ID_PATTERN.search(ln)]


def _default_metadata(text: str, category: str, metadata: dict | None = None) -> dict[str, Any]:
    meta = dict(metadata or {})
    source_count = len(set(SOURCE_ID_PATTERN.findall(text)))
    source_rows = meta.get("sources", [])
    if source_rows and isinstance(source_rows, list):
        source_count = len(source_rows)
    direct_quotes = _extract_quotes(text)
    sections = HEADER_RE.findall(text)
    questions = [ln for ln in text.splitlines() if ln.strip().startswith(("Q.", "Q1", "Q2", "Q3", "Q4", "Q5", "Q:"))]
    follow_ups = [ln for ln in text.splitlines() if "후속" in ln or "추가 질문" in ln or "꼬리 질문" in ln]
    editor_notes = [ln for ln in text.splitlines() if "편집자 주" in ln or "Editor note" in ln]
    pros = len(re.findall(r"\bPros\b|^\s*[-*]\s*\+", text, flags=re.MULTILINE))
    cons = len(re.findall(r"\bCons\b|^\s*[-*]\s*[-−]", text, flags=re.MULTILINE))
    competitor_count = max(0, len(re.findall(r"\|\s*[^|\n]+\s*\|", text)) - 1)
    quantitative_claims = len(NUMBER_RE.findall(text))
    sourced_lines = _source_lines(text)
    sourced_ratio = round(min(1.0, len(sourced_lines) / max(1, quantitative_claims)), 2)
    has_con_section = any("반대" in s or "비판" in s or "counter" in s.lower() for s in sections)
    has_chart = "chart" in text.lower() or "차트" in text
    chart_source_id = bool(re.search(r"차트.*?(?:\[src-|\(source_id:)", text, re.IGNORECASE | re.DOTALL))
    trend_presence = any(k in text for k in ("상승", "하락", "횡보", "증가", "감소"))
    key_takeaway_count = len(re.findall(r"핵심 요점\s*\d|takeaway\s*\d", text, re.IGNORECASE))
    if key_takeaway_count == 0:
        key_takeaway_count = len(re.findall(r"^- .*", text, flags=re.MULTILINE))
    portrait = "portrait" in text.lower() or "/covers/" in text or "사진" in text

    ko_official = 0
    en_official = 0
    for source in source_rows:
        if not isinstance(source, dict):
            continue
        language = source.get("language")
        is_official = bool(source.get("is_official"))
        if language == "ko" and is_official:
            ko_official += 1
        if language == "en" and is_official:
            en_official += 1

    if source_rows and category == "deep_dive" and not (ko_official or en_official):
        ko_official = sum(1 for s in source_rows if isinstance(s, dict) and s.get("language") == "ko")
        en_official = sum(1 for s in source_rows if isinstance(s, dict) and s.get("language") == "en")

    return {
        **meta,
        "words": _count_words(text),
        "count": len(direct_quotes),
        "source_count": source_count,
        "ko_official": ko_official,
        "en_official": en_official,
        "sourced_ratio": sourced_ratio,
        "has_con_section": has_con_section,
        "pros": pros or int("Pros" in text),
        "cons": cons or int("Cons" in text),
        "competitor_count": meta.get("competitor_count", competitor_count),
        "has_chart": meta.get("has_chart", has_chart),
        "chart_source_id": meta.get("chart_source_id", chart_source_id),
        "follow_up_ratio": meta.get("follow_up_ratio", round(min(1.0, len(follow_ups) / max(1, len(questions))), 2)),
        "max_words": max((len(WORD_RE.findall(x)) for x in editor_notes), default=0),
        "presence": (
            ("AI 사용 고지" in text or "AI 보조" in text or "AI 활용" in text)
            if category != "insight" else trend_presence
        ),
        "coverage": round(min(1.0, len(_source_lines(text)) / max(1, len(_split_sentences(text)))), 2),
        "subject_portrait": portrait,
        "pull_quote_count": len(direct_quotes),
        "section_count": len(sections),
        "quantitative_claims_count": quantitative_claims,
        "key_takeaway_count": key_takeaway_count,
        "correction_policy_presence": bool(re.search(r"정정.*24\s*시간|24h|24 hours", text, re.IGNORECASE)),
        "source_id_coverage": round(min(1.0, len(_source_lines(text)) / max(1, len(_split_sentences(text)))), 2),
        "ai_disclosure_presence": ("AI 사용 고지" in text or "AI 보조" in text or "AI 활용" in text),
        "trend_direction_presence": trend_presence,
    }


def _tokenize(expr: str) -> list[str]:
    return [tok for tok in re.split(r"\s+", expr.strip()) if tok]


def _coerce(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+)?", value):
        return float(value) if "." in value else int(value)
    return value


def _eval_simple(tokens: list[str], metrics: dict[str, Any], rule_id: str) -> tuple[bool, str, str]:
    expr = " ".join(tokens)
    if expr == "presence":
        if rule_id == "source-id-coverage":
            actual = metrics.get("source_id_coverage", 0.0)
            return actual == 1.0, f"{actual:.2f}", "1.00"
        if rule_id == "ai-disclosure":
            actual = bool(metrics.get("ai_disclosure_presence"))
            return actual, str(actual).lower(), "true"
        if rule_id == "correction-policy":
            actual = bool(metrics.get("correction_policy_presence"))
            return actual, str(actual).lower(), "true"
        if rule_id == "subject-portrait":
            actual = bool(metrics.get("subject_portrait"))
            return actual, str(actual).lower(), "true"
        if rule_id == "trend-direction":
            actual = bool(metrics.get("trend_direction_presence"))
            return actual, str(actual).lower(), "true"
        actual = bool(metrics.get("presence"))
        return actual, str(actual).lower(), "true"
    if expr == "100% coverage":
        actual = metrics.get("coverage", metrics.get("source_id_coverage", 0.0))
        return actual == 1.0, f"{actual:.2f}", "1.00"
    if expr and len(tokens) == 1 and tokens[0] in metrics:
        actual = bool(metrics[tokens[0]])
        return actual, str(actual).lower(), "true"
    if len(tokens) == 3:
        left, op, right = tokens
        actual = _coerce(metrics.get(left, 0))
        expected = _coerce(right)
        passed = {
            ">=": actual >= expected,
            "<=": actual <= expected,
            "==": actual == expected,
            ">": actual > expected,
            "<": actual < expected,
        }[op]
        return passed, str(actual), f"{op} {expected}"
    if len(tokens) == 5 and tokens[1] in {"<=", "<"} and tokens[3] in {"<=", "<"}:
        low, op1, key, op2, high = tokens
        actual = _coerce(metrics.get(key, 0))
        low_v = _coerce(low)
        high_v = _coerce(high)
        lower_ok = actual >= low_v if op1 == "<=" else actual > low_v
        upper_ok = actual <= high_v if op2 == "<=" else actual < high_v
        return lower_ok and upper_ok, str(actual), f"{low_v}..{high_v}"
    raise ValueError(f"unsupported measure expression: {expr}")


def _evaluate_measure(expr: str, metrics: dict[str, Any], rule_id: str) -> tuple[bool, str, str]:
    parts = re.split(r"\s+(AND|OR)\s+", expr.strip())
    result: tuple[bool, str, str] | None = None
    current_op: str | None = None
    for part in parts:
        if part in {"AND", "OR"}:
            current_op = part
            continue
        sub = _eval_simple(_tokenize(part), metrics, rule_id)
        if result is None:
            result = sub
            continue
        assert current_op is not None
        passed = result[0] and sub[0] if current_op == "AND" else result[0] or sub[0]
        result = (passed, f"{result[1]} {current_op} {sub[1]}", f"{result[2]} {current_op} {sub[2]}")
    if result is None:
        raise ValueError("empty measure")
    return result


def measure_metric(rule_id: str, text: str, metadata: dict | None = None) -> dict:
    metrics = _default_metadata(text, metadata.get("category", "") if metadata else "", metadata)
    if rule_id == "source-count":
        metrics["count"] = metrics.get("source_count", 0)
    elif rule_id == "direct-quotes":
        metrics["count"] = len(_extract_quotes(text))
    elif rule_id == "editor-notes-limit":
        metrics["count"] = len([ln for ln in text.splitlines() if "편집자 주" in ln or "Editor note" in ln])
    elif rule_id == "criteria-scored":
        metrics["count"] = len(re.findall(r"\b(?:score|점수)\b|^\s*[-*]\s*.*\d+(?:\.\d+)?/10", text, flags=re.MULTILINE))
    elif rule_id == "pull-quote-count":
        metrics["count"] = len(_extract_quotes(text))
    elif rule_id == "section-count":
        metrics["count"] = len(HEADER_RE.findall(text))
    elif rule_id == "quantitative-claims":
        metrics["count"] = metrics.get("quantitative_claims_count", 0)
    elif rule_id == "key-takeaway":
        metrics["count"] = metrics.get("key_takeaway_count", 0)
    return metrics


def _build_check(rule: dict[str, Any], text: str, category: str, metadata: dict[str, Any]) -> dict[str, Any]:
    metric_data = measure_metric(rule["id"], text, {**metadata, "category": category})
    passed, measured, expected = _evaluate_measure(rule["measure"], metric_data, rule["id"])
    return {
        "id": rule["id"],
        "rule": rule["rule"],
        "status": "pass" if passed else "fail",
        "measured": measured,
        "expected": expected,
    }


def check_article(
    draft_path: str,
    category: str,
    metadata: dict | None = None,
) -> dict:
    standards = load_standards()
    categories = standards["categories"]
    if category not in categories:
        raise ValueError(f"unknown category: {category}")

    text = Path(draft_path).read_text(encoding="utf-8")
    metadata = dict(metadata or {})

    common_checks = [
        _build_check(rule, text, category, metadata)
        for rule in standards["common"]["must_pass"]
    ]
    category_checks = [
        _build_check(rule, text, category, metadata)
        for rule in categories[category]["must_pass"]
    ]
    should_rules = categories[category].get("should_pass", [])
    should_checks = [
        _build_check(rule, text, category, metadata)
        for rule in should_rules
    ]

    must_pass_total = len(common_checks) + len(category_checks)
    must_pass_passed = sum(1 for item in common_checks + category_checks if item["status"] == "pass")
    should_pass_total = len(should_checks)
    should_pass_passed = sum(1 for item in should_checks if item["status"] == "pass")

    return {
        "category": category,
        "common_checks": common_checks,
        "category_checks": category_checks,
        "should_checks": should_checks,
        "must_pass_total": must_pass_total,
        "must_pass_passed": must_pass_passed,
        "should_pass_total": should_pass_total,
        "should_pass_passed": should_pass_passed,
        "can_publish": must_pass_total == must_pass_passed,
    }


def _list_categories() -> int:
    standards = load_standards()
    for name in standards["categories"].keys():
        print(name)
    return 0


def _smoke_test() -> None:
    sample = (
        "# Deep dive sample [src-001]\n\n"
        "AI 사용 고지와 정정 정책은 하단에 있다 [src-002]. 수치 30% 증가 [src-003].\n\n"
        "## 반대 관점 [src-004]\n"
        "\"첫 번째 인용\" [src-005]\n"
        "\"두 번째 인용\" [src-006]\n"
        "정정 정책: correction@example.com, 24시간 내 응답\n"
        "AI 사용 고지: Claude 보조 사용\n"
    )
    tmp = ROOT / "drafts" / "_standards_smoke.md"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(sample, encoding="utf-8")
    result = check_article(
        str(tmp),
        "insight",
        metadata={"has_chart": True, "chart_source_id": True},
    )
    assert result["category"] == "insight"
    assert result["must_pass_total"] >= 1
    tmp.unlink(missing_ok=True)
    print("✓ standards_checker 스모크 테스트 통과")


def main() -> int:
    parser = argparse.ArgumentParser(description="기사 기준 스펙 검사기")
    parser.add_argument("--draft", help="검사할 draft 경로")
    parser.add_argument("--category", help="카테고리")
    parser.add_argument("--metadata", help="JSON metadata 문자열")
    parser.add_argument("--list-categories", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list_categories:
        return _list_categories()
    if not args.draft or not args.category:
        parser.error("--draft 와 --category 가 필요합니다")
    metadata = json.loads(args.metadata) if args.metadata else None
    result = check_article(args.draft, args.category, metadata)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "category": result["category"],
            "must_pass": f"{result['must_pass_passed']}/{result['must_pass_total']}",
            "should_pass": f"{result['should_pass_passed']}/{result['should_pass_total']}",
            "can_publish": result["can_publish"],
        }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _smoke_test()
    else:
        raise SystemExit(main())
