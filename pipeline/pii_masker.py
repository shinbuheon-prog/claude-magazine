"""
PII 비식별화 파이프라인 (TASK_017)
- 10개 패턴을 탐지하여 결정적 토큰으로 마스킹한다.
- 한국 이름은 Claude Haiku 4.5 NER로 보조 탐지한다 (API 키 없으면 skip).
- 마스킹 ↔ 복원이 round-trip 되도록 역매핑 JSON을 별도 저장한다.

사용 예:
    python pipeline/pii_masker.py --input interview.md --output masked.md --mapping-out mapping.json
    cat interview.md | python pipeline/pii_masker.py > masked.md
    python pipeline/pii_masker.py --restore masked.md --mapping mapping.json --output restored.md
    python pipeline/pii_masker.py --input interview.md --detect-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv():  # type: ignore
        return False

load_dotenv()

# Windows 콘솔 UTF-8 출력 깨짐 방지
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAPPING_DIR = ROOT / "data" / "pii_mappings"
LOGS_DIR = ROOT / "logs"

HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_TIMEOUT_SECONDS = float(os.environ.get("PII_HAIKU_TIMEOUT_SECONDS", "5"))
HAIKU_ENABLED = os.environ.get("PII_HAIKU_ENABLED", "").lower() in {"1", "true", "yes", "on"}

# ---------------------------------------------------------------------------
# 패턴 정의 (탐지 우선순위 순)
# ---------------------------------------------------------------------------
# 한국 시/도/광역시 (도/특별시/광역시/특별자치시/특별자치도)
KR_REGIONS = (
    "서울특별시|서울|부산광역시|부산|대구광역시|대구|인천광역시|인천|"
    "광주광역시|광주|대전광역시|대전|울산광역시|울산|"
    "세종특별자치시|세종|경기도|경기|강원특별자치도|강원도|강원|"
    "충청북도|충북|충청남도|충남|전라북도|전북|전북특별자치도|"
    "전라남도|전남|경상북도|경북|경상남도|경남|제주특별자치도|제주도|제주"
)

# 토큰 prefix ↔ 분류 매핑
TYPE_TO_PREFIX = {
    "KRN": "KRN",          # 주민등록번호
    "PHONE": "PHONE",
    "EMAIL": "EMAIL",
    "CARD": "CARD",
    "ACCT": "ACCT",
    "BIZ": "BIZ",
    "PERSON": "PERSON",
    "SYSTEM": "SYSTEM",    # 회사 내부 시스템명
    "ADDR": "ADDR",
    "IP": "IP",
}

# (type, compiled pattern) — 우선순위 순 (더 구체적인 패턴이 먼저)
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("KRN", re.compile(r"\b\d{6}-[1-4]\d{6}\b")),
    ("PHONE", re.compile(r"\b01[0-9]-\d{3,4}-\d{4}\b")),
    ("CARD", re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")),
    ("BIZ", re.compile(r"\b\d{3}-\d{2}-\d{5}\b")),
    # 계좌번호는 CARD/BIZ 이후 (더 느슨한 패턴)
    ("ACCT", re.compile(r"\b\d{3,6}-\d{2,6}-\d{4,10}\b")),
    # 이메일 (RFC 5322 실용 서브셋)
    ("EMAIL", re.compile(
        r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
    )),
    # IPv6 — 먼저 매칭 (IPv4보다 구체적)
    ("IP", re.compile(
        r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b"
    )),
    # IPv4
    ("IP", re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
    )),
    # 주소: 시/도 + (시|군|구) + (동|읍|면|로|길) + 번지
    ("ADDR", re.compile(
        rf"(?:{KR_REGIONS})\s*[^\s,]*?(?:시|군|구)?\s*[^\s,]+?(?:동|읍|면|로|길)\s*\d+(?:[-–]\d+)?"
    )),
]

PERSON_CONTEXT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:인터뷰이|기자|작성자|담당자|발표자|문의|제보자)\s*[:：]?\s*([가-힣]{2,4})"),
    re.compile(r"\b([가-힣]{2,4})\s*(?:씨|님|기자|대표|교수|변호사|연구원)\b"),
]


# ---------------------------------------------------------------------------
# 매핑 구조: dict[str, str]  (token -> original)
# Reverse map(original -> token)은 내부에서 파생 → 결정적 마스킹 보장
# ---------------------------------------------------------------------------
def _load_internal_terms(internal_terms: list[str] | None) -> list[str]:
    if internal_terms:
        return [t for t in internal_terms if t]
    raw = os.environ.get("PII_INTERNAL_TERMS", "")
    terms = [t.strip() for t in raw.split(",") if t.strip()]
    return terms


def _reverse_map(mapping: dict) -> dict[str, str]:
    return {v: k for k, v in mapping.items()}


def _next_token(ptype: str, mapping: dict) -> str:
    prefix = TYPE_TO_PREFIX[ptype]
    count = sum(1 for t in mapping if t.startswith(f"[{prefix}_"))
    return f"[{prefix}_{count + 1:03d}]"


def _assign_token(value: str, ptype: str, mapping: dict) -> str:
    """결정적 마스킹: 같은 값이 이미 있으면 같은 토큰 재사용."""
    rev = _reverse_map(mapping)
    if value in rev:
        return rev[value]
    token = _next_token(ptype, mapping)
    mapping[token] = value
    return token


def _literal_positions(text: str, value: str) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    start = 0
    while True:
        idx = text.find(value, start)
        if idx < 0:
            break
        end = idx + len(value)
        positions.append((idx, end))
        start = end
    return positions


def _heuristic_extract_person_names(text: str) -> list[str]:
    names: list[str] = []
    for pattern in PERSON_CONTEXT_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            if len(name) < 2:
                continue
            if name not in names:
                names.append(name)
    return names


# ---------------------------------------------------------------------------
# Haiku NER (한국 이름 탐지)
# ---------------------------------------------------------------------------
def _haiku_extract_person_names(text: str) -> list[str]:
    """
    Claude Haiku 4.5에게 사람 이름만 JSON 배열로 추출하도록 요청.
    ANTHROPIC_API_KEY 없으면 빈 리스트 반환 (패턴 기반만 사용).
    """
    if not HAIKU_ENABLED:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[pii] ANTHROPIC_API_KEY 미설정 — Haiku NER skip", file=sys.stderr)
        return []

    try:
        import anthropic  # type: ignore
    except ImportError:
        print("[pii] anthropic 패키지 없음 — Haiku NER skip", file=sys.stderr)
        return []

    client = anthropic.Anthropic(api_key=api_key, timeout=HAIKU_TIMEOUT_SECONDS)
    system_prompt = (
        "당신은 한국어 텍스트에서 사람 이름만 추출하는 NER 엔진이다.\n"
        "- 오직 실제 사람 이름(성+이름 또는 이름)만 추출한다.\n"
        "- 회사명·제품명·지명·직책·일반명사는 제외한다.\n"
        "- 반드시 JSON 배열 하나만 출력. 예: [\"홍길동\",\"김철수\"]\n"
        "- 이름이 없으면 빈 배열 [] 을 출력."
    )
    user_prompt = f"<text>\n{text}\n</text>"

    try:
        result_text = ""
        request_id = None
        with client.messages.stream(
            model=HAIKU_MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                result_text += chunk
            final = stream.get_final_message()
            request_id = getattr(final, "_request_id", None)

        LOGS_DIR.mkdir(exist_ok=True)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "model": HAIKU_MODEL,
            "purpose": "pii_person_ner",
        }
        log_file = (
            LOGS_DIR
            / f"pii_ner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        log_file.write_text(
            json.dumps(log_entry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # JSON 배열 추출 (앞뒤 설명 붙는 경우 대비)
        match = re.search(r"\[.*\]", result_text, flags=re.S)
        if not match:
            return []
        names = json.loads(match.group(0))
        return [str(n).strip() for n in names if isinstance(n, str) and n.strip()]
    except Exception as exc:  # noqa: BLE001
        print(f"[pii] Haiku NER 실패 — skip ({exc})", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# 핵심 API
# ---------------------------------------------------------------------------
def detect_pii(text: str, internal_terms: list[str] | None = None) -> list[dict]:
    """마스킹 없이 탐지 결과만 반환."""
    detections: list[dict] = []
    taken: list[tuple[int, int]] = []

    def overlap(start: int, end: int) -> bool:
        for s, e in taken:
            if start < e and end > s:
                return True
        return False

    # 1) 정규식 패턴
    for ptype, pattern in PATTERNS:
        for m in pattern.finditer(text):
            if overlap(m.start(), m.end()):
                continue
            taken.append((m.start(), m.end()))
            detections.append(
                {"type": ptype, "value": m.group(0), "position": [m.start(), m.end()]}
            )

    # 2) 내부 시스템명 (literal 매칭)
    terms = _load_internal_terms(internal_terms)
    for term in terms:
        if not term:
            continue
        start = 0
        while True:
            idx = text.find(term, start)
            if idx < 0:
                break
            end = idx + len(term)
            if not overlap(idx, end):
                taken.append((idx, end))
                detections.append(
                    {"type": "SYSTEM", "value": term, "position": [idx, end]}
                )
            start = end

    # 3) 문맥 기반 한국 이름 휴리스틱
    names = _heuristic_extract_person_names(text)
    for name in names:
        if not name:
            continue
        for idx, end in _literal_positions(text, name):
            if overlap(idx, end):
                continue
            taken.append((idx, end))
            detections.append(
                {"type": "PERSON", "value": name, "position": [idx, end]}
            )

    # 4) Haiku 한국 이름 NER 보강
    names = _haiku_extract_person_names(text)
    for name in names:
        if not name:
            continue
        for idx, end in _literal_positions(text, name):
            if overlap(idx, end):
                continue
            taken.append((idx, end))
            detections.append(
                {"type": "PERSON", "value": name, "position": [idx, end]}
            )

    detections.sort(key=lambda d: (d["position"][0], d["position"][1]))
    return detections


def mask_text(
    text: str,
    internal_terms: list[str] | None = None,
    mapping: dict | None = None,
) -> tuple[str, dict]:
    """
    텍스트를 마스킹하고 (masked_text, mapping_dict)를 반환한다.
    mapping을 전달하면 기존 매핑에 이어서 번호를 부여 (reset 방지).
    """
    if mapping is None:
        mapping = {}

    detections = detect_pii(text, internal_terms=internal_terms)
    # 우선 모든 발견값에 대해 토큰 할당 (결정적)
    for d in detections:
        _assign_token(d["value"], d["type"], mapping)

    # 긴 값부터 치환해야 부분일치로 인한 덮어쓰기를 방지
    rev = _reverse_map(mapping)
    ordered_values = sorted(rev.keys(), key=lambda v: (-len(v), v))

    masked = text
    for value in ordered_values:
        token = rev[value]
        # 이스케이프하여 단순 literal 치환
        masked = masked.replace(value, token)
    return masked, mapping


def restore_text(masked_text: str, mapping: dict) -> str:
    """토큰을 원문으로 복원."""
    restored = masked_text
    # 긴 토큰부터 (안전)
    for token in sorted(mapping.keys(), key=lambda t: (-len(t), t)):
        restored = restored.replace(token, mapping[token])
    return restored


def with_pii_protection(claude_call_fn, text: str, **kwargs):
    """
    claude_call_fn(masked_text, **kwargs) 형태로 호출.
    내부: mask_text → Claude 호출 → restore_text 순.
    """
    internal_terms = kwargs.pop("internal_terms", None)
    masked, mapping = mask_text(text, internal_terms=internal_terms)
    response = claude_call_fn(masked, **kwargs)
    if isinstance(response, str):
        return restore_text(response, mapping)
    # 문자열이 아니면 그대로 반환 — 호출자가 책임
    return response


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _count_by_type(mapping: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in mapping:
        # token format: [TYPE_NNN]
        m = re.match(r"\[([A-Z]+)_\d+\]", token)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def _print_summary(
    input_label: str,
    input_bytes: int,
    mapping: dict,
    output_label: str,
    output_bytes: int,
    mapping_path: Path | None,
) -> None:
    print("=== PII 비식별화 ===", file=sys.stderr)
    print(f"입력: {input_label} ({input_bytes:,} bytes)", file=sys.stderr)
    print("", file=sys.stderr)
    print("탐지:", file=sys.stderr)
    counts = _count_by_type(mapping)
    if not counts:
        print("  (탐지 없음)", file=sys.stderr)
    else:
        for ptype, n in sorted(counts.items()):
            print(f"  - {ptype}: {n}건", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"출력: {output_label} ({output_bytes:,} bytes)", file=sys.stderr)
    if mapping_path:
        print(
            f"매핑: {mapping_path} ({len(mapping)} entries)",
            file=sys.stderr,
        )
    print("", file=sys.stderr)
    print("매핑 파일은 민감 — data/ 외부로 유출 금지", file=sys.stderr)


def _default_mapping_path(output_path: Path | None) -> Path:
    DEFAULT_MAPPING_DIR.mkdir(parents=True, exist_ok=True)
    stem = output_path.stem if output_path else "pii"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_MAPPING_DIR / f"{stem}_mapping_{ts}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="PII 비식별화 파이프라인")
    parser.add_argument("--input", help="입력 파일 경로 (생략 시 stdin)")
    parser.add_argument("--output", help="출력 파일 경로 (생략 시 stdout)")
    parser.add_argument("--mapping-out", help="역매핑 JSON 저장 경로")
    parser.add_argument("--detect-only", action="store_true", help="탐지만 수행")
    parser.add_argument("--restore", help="복원 대상 마스킹 텍스트 파일")
    parser.add_argument("--mapping", help="--restore용 매핑 JSON 경로")
    parser.add_argument(
        "--internal-terms",
        help="쉼표로 구분된 내부 시스템명 (미지정 시 env PII_INTERNAL_TERMS)",
    )
    parser.add_argument("--dry-run", action="store_true", help="파일 쓰기 없이 미리보기")
    args = parser.parse_args()

    # ----- 복원 모드 -----
    if args.restore:
        if not args.mapping:
            print("--restore 는 --mapping 필요", file=sys.stderr)
            return 2
        masked = Path(args.restore).read_text(encoding="utf-8")
        mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
        restored = restore_text(masked, mapping)
        if args.output and not args.dry_run:
            Path(args.output).write_text(restored, encoding="utf-8")
            print(f"복원 완료: {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(restored)
        return 0

    # ----- 입력 로드 -----
    if args.input:
        input_path = Path(args.input)
        text = input_path.read_text(encoding="utf-8")
        input_label = str(input_path)
    else:
        # stdin은 UTF-8로 강제 디코딩
        raw = sys.stdin.buffer.read()
        text = raw.decode("utf-8", errors="replace")
        input_label = "<stdin>"
    input_bytes = len(text.encode("utf-8"))

    internal_terms: list[str] | None = None
    if args.internal_terms:
        internal_terms = [t.strip() for t in args.internal_terms.split(",") if t.strip()]

    # ----- 탐지만 -----
    if args.detect_only:
        detections = detect_pii(text, internal_terms=internal_terms)
        if args.output and not args.dry_run:
            Path(args.output).write_text(
                json.dumps(detections, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"탐지 결과 저장: {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(json.dumps(detections, ensure_ascii=False, indent=2))
            sys.stdout.write("\n")
        return 0

    # ----- 마스킹 -----
    masked, mapping = mask_text(text, internal_terms=internal_terms)

    if args.output and not args.dry_run:
        out_path = Path(args.output)
        out_path.write_text(masked, encoding="utf-8")
        output_label = str(out_path)
    else:
        out_path = None
        sys.stdout.write(masked)
        output_label = "<stdout>"
    output_bytes = len(masked.encode("utf-8"))

    mapping_path: Path | None = None
    if not args.dry_run:
        if args.mapping_out:
            mapping_path = Path(args.mapping_out)
            mapping_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # 기본: data/pii_mappings/ 에 자동 저장
            mapping_path = _default_mapping_path(out_path)
        mapping_path.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    _print_summary(
        input_label=input_label,
        input_bytes=input_bytes,
        mapping=mapping,
        output_label=output_label,
        output_bytes=output_bytes,
        mapping_path=mapping_path,
    )
    return 0


# ---------------------------------------------------------------------------
# 스모크 테스트
# ---------------------------------------------------------------------------
def _smoke_test() -> None:
    sample = (
        "인터뷰이: 홍길동 (010-1234-5678, hong@example.com)\n"
        "주민번호: 900101-1234567\n"
        "신용카드: 1234-5678-9012-3456\n"
        "사업자번호: 123-45-67890\n"
        "계좌번호: 110-123-456789\n"
        "회사 내부 시스템: InternalERP-X\n"
        "서버 IP: 192.168.0.1 (IPv6: 2001:db8::1)\n"
        "주소: 서울특별시 강남구 테헤란로 123\n"
        "다시 등장하는 홍길동과 hong@example.com.\n"
    )
    masked, mapping = mask_text(sample, internal_terms=["InternalERP-X"])
    restored = restore_text(masked, mapping)
    assert restored == sample, "round-trip 실패"
    # 결정적 마스킹 확인
    assert masked.count("[EMAIL_001]") == 2
    # 오프라인에서도 10개 분류가 모두 동작해야 한다.
    for expect in ["KRN", "PHONE", "EMAIL", "CARD", "BIZ", "ACCT", "IP", "ADDR", "SYSTEM", "PERSON"]:
        assert any(t.startswith(f"[{expect}_") for t in mapping), f"{expect} 탐지 실패"
    print("[smoke] OK — mapping entries:", len(mapping))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        _smoke_test()
    else:
        raise SystemExit(main())
