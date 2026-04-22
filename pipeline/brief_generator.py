"""
기사 브리프 생성기
모델: claude-sonnet-4-6
사용법: python pipeline/brief_generator.py --topic "TOPIC" [--sources src1.md src2.md] [--out brief.json] [--dry-run]
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

try:
    from pipeline.observability import log_usage, start_trace
except ModuleNotFoundError:
    from observability import log_usage, start_trace

try:
    from pipeline.source_diversity import check_diversity
except ModuleNotFoundError:
    try:
        from source_diversity import check_diversity  # type: ignore
    except ModuleNotFoundError:
        check_diversity = None  # type: ignore

try:
    from pipeline.heuristics_injector import inject_heuristics
except ModuleNotFoundError:
    try:
        from heuristics_injector import inject_heuristics  # type: ignore
    except ModuleNotFoundError:
        def inject_heuristics(category: str, max_examples: int = 10) -> str:
            return ""

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

BRIEF_REQUIRED_KEYS = {
    "working_title",
    "angle",
    "why_now",
    "outline",
    "evidence_map",
    "unknowns",
    "risk_flags",
}


def load_template() -> str:
    return (PROMPTS_DIR / "template_A_brief.txt").read_text(encoding="utf-8")


def load_sources(source_paths: list[str]) -> str:
    if not source_paths:
        return "(소스 없음 — 웹 검색 결과나 직접 입력한 텍스트를 여기에 붙여넣으세요)"

    parts: list[str] = []
    for raw_path in source_paths:
        path = Path(raw_path)
        if path.exists():
            parts.append(f"=== {path.name} ===\n{path.read_text(encoding='utf-8')}")
        else:
            parts.append(f"=== {raw_path} ===\n(파일을 찾을 수 없음)")
    return "\n\n".join(parts)


def _extract_json_block(text: str) -> dict:
    json_start = text.find("{")
    json_end = text.rfind("}")
    if json_start < 0 or json_end < json_start:
        raise ValueError("응답에서 JSON 객체를 찾지 못했습니다.")
    return json.loads(text[json_start : json_end + 1])


def _validate_brief_schema(brief: dict) -> None:
    missing = BRIEF_REQUIRED_KEYS - set(brief.keys())
    if missing:
        raise ValueError(f"브리프 필수 키 누락: {sorted(missing)}")

    if not isinstance(brief["outline"], list):
        raise ValueError("'outline'은 list여야 합니다.")
    for index, item in enumerate(brief["outline"]):
        if not isinstance(item, dict):
            raise ValueError(f"'outline[{index}]'은 dict여야 합니다.")
        if "section" not in item or "points" not in item:
            raise ValueError(f"'outline[{index}]'에 'section' 또는 'points'가 없습니다.")
        if not isinstance(item["points"], list):
            raise ValueError(f"'outline[{index}].points'는 list여야 합니다.")

    if not isinstance(brief["evidence_map"], list):
        raise ValueError("'evidence_map'은 list여야 합니다.")
    for index, item in enumerate(brief["evidence_map"]):
        if not isinstance(item, dict):
            raise ValueError(f"'evidence_map[{index}]'은 dict여야 합니다.")
        if "claim" not in item or "source_id" not in item:
            raise ValueError(f"'evidence_map[{index}]'에 'claim' 또는 'source_id'가 없습니다.")

    for key in ("working_title", "angle", "why_now"):
        if not isinstance(brief[key], str):
            raise ValueError(f"'{key}'는 string이어야 합니다.")

    for key in ("unknowns", "risk_flags"):
        if not isinstance(brief[key], list):
            raise ValueError(f"'{key}'는 list여야 합니다.")


def _write_log(topic: str, request_id: str | None, input_tokens: int, output_tokens: int) -> Path:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id,
        "model": "claude-sonnet-4-6",
        "topic": topic,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    log_file = LOGS_DIR / f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[log] request_id={request_id} -> {log_file.name}", file=sys.stderr)
    return log_file


def _build_dry_run_brief(topic: str) -> dict:
    return {
        "working_title": f"{topic}: 핵심 쟁점 브리프",
        "angle": "공개된 출처만으로 실무적 의미를 정리한다.",
        "why_now": "현재 배포·가격·정책 변화가 의사결정에 직접 영향을 준다.",
        "outline": [
            {
                "section": "핵심 변화",
                "points": ["이번 업데이트의 주요 변경점", "실무자에게 미치는 영향"],
            },
            {
                "section": "리스크와 확인 필요 항목",
                "points": ["확정되지 않은 정보", "추가 검증이 필요한 주장"],
            },
        ],
        "evidence_map": [{"claim": "브리프 드라이런 샘플", "source_id": "UNKNOWN"}],
        "unknowns": ["실제 API 호출 전 최신 1차 출처 재확인 필요"],
        "risk_flags": ["드라이런 결과이므로 실제 발행 전 검증 필요"],
    }


def _run_diversity_gate(article_id: str, strict: bool = False) -> dict | None:
    """
    TASK_019: 브리프 생성 전에 소스 다양성을 검사한다.
    실패해도 기본은 경고만 찍고 계속 진행. strict=True면 sys.exit(1).
    check_diversity import 실패 시 None 반환 (파이프라인을 깨뜨리지 않음).
    """
    if not article_id or check_diversity is None:
        return None
    try:
        diversity = check_diversity(article_id)
    except Exception as exc:
        print(f"[warn] 소스 다양성 검사 실패 (skip): {exc}", file=sys.stderr)
        return None

    if not diversity["passed"]:
        print(f"⚠️  소스 다양성: {diversity['summary']}", file=sys.stderr)
        for rec in diversity["recommendations"]:
            print(f"   권고: {rec}", file=sys.stderr)
        if strict:
            print("[strict] 소스 다양성 규칙 실패 — 발행 중단", file=sys.stderr)
            sys.exit(1)
    return diversity


def generate_brief(
    topic: str,
    source_bundle: str,
    dry_run: bool = False,
    article_id: str = "",
    strict_diversity: bool = False,
    category: str = "all",
) -> dict:
    # TASK_019 통합: article_id가 있으면 소스 다양성 검사
    _run_diversity_gate(article_id, strict=strict_diversity)

    if dry_run:
        brief = _build_dry_run_brief(topic)
        brief["category"] = category
        _validate_brief_schema(brief)
        _write_log(topic, "dry-run", 0, 0)
        return brief

    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = load_template()
    heuristics_block = inject_heuristics(category)

    system_prompt = (
        "당신은 한국어 B2B 기술 매체의 수석 편집자다.\n"
        "제공된 출처에만 근거하라.\n"
        "원문에 없는 주장, 수치, 인용은 만들지 말라.\n"
        "출력은 지정된 JSON만 반환하라."
    )
    if heuristics_block:
        system_prompt += "\n\n" + heuristics_block
    user_prompt = template.replace("{{topic}}", topic).replace("{{source_bundle}}", source_bundle)

    result_text = ""
    request_id = None
    input_tokens = 0
    output_tokens = 0
    trace = start_trace(name="brief_generation", model="claude-sonnet-4-6", topic=topic)

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            result_text += text
        final = stream.get_final_message()
        request_id = getattr(final, "_request_id", None)
        input_tokens = final.usage.input_tokens
        output_tokens = final.usage.output_tokens

    brief = _extract_json_block(result_text)
    brief.setdefault("category", category)
    _validate_brief_schema(brief)
    log_usage(
        getattr(trace, "id", None),
        input_tokens,
        output_tokens,
        "claude-sonnet-4-6",
        request_id=request_id,
    )
    _write_log(topic, request_id, input_tokens, output_tokens)
    return brief


def main() -> None:
    parser = argparse.ArgumentParser(description="기사 브리프 생성기")
    parser.add_argument("--topic", required=True, help="기사 주제")
    parser.add_argument("--sources", nargs="*", default=[], help="소스 파일 경로들")
    parser.add_argument("--out", help="출력 JSON 파일 경로 (생략 시 stdout)")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 샘플 브리프 생성")
    parser.add_argument("--article-id", dest="article_id", default="", help="소스 다양성 검사에 사용할 article_id")
    parser.add_argument("--strict-diversity", action="store_true", help="소스 다양성 실패 시 중단 (exit 1)")
    parser.add_argument("--category", default="all", help="editor heuristics category")
    args = parser.parse_args()

    source_bundle = load_sources(args.sources)
    brief = generate_brief(
        args.topic,
        source_bundle,
        dry_run=args.dry_run,
        article_id=args.article_id,
        strict_diversity=args.strict_diversity,
        category=args.category,
    )
    output = json.dumps(brief, ensure_ascii=False, indent=2)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"브리프 저장 완료: {args.out}")
        return

    print(output)


if __name__ == "__main__":
    main()
