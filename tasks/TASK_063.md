# TASK_063 — source_diversity "한국어 1 + 원문 1 + 반대 관점 1" 패턴 강제

## 메타
- **status**: todo
- **prerequisites**: TASK_019 (source_diversity 4 규칙)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화 — 검수 강화)

---

## 목적

기존 source_diversity는 4 규칙(언어·관점·발행처·시효성)만 강제. 외부 컨설팅 보고서 §"소스 다양성 규칙" 권장 패턴 추가:

> "한국어 공식 문서 1개 이상 + 원문 공식 문서 1개 이상 + 반대 관점 또는 영향권자 자료 1개 이상"

본 태스크는 이 패턴을 **5번째 규칙**으로 추가 + editorial_lint·publish-gate 자동 검증.

## 해결하는 운영 상황

- 5월 호 발행 사이클 시점 16 꼭지 × 본 패턴 자동 점검
- 단일 source 또는 단일 언어 source만으로 작성된 본문 차단
- AI 모델 편향·과도한 안전 필터링으로 인한 특정 이슈 누락 방지
- 매거진 정체성 — "한국어권 Claude 실무자 + 비즈니스 의사결정자 (둘 다)" 청중 정합

## 구현 단계

### 1. `pipeline/source_diversity.py` 5번째 규칙 추가
기존 4 규칙:
1. 언어 다양성 (≥ 2 언어)
2. 관점 다양성 (≥ 2 stance)
3. 발행처 다양성 (≥ 3 publisher)
4. 시효성 (최신 source ≥ 30일 이내)

신규 규칙 5: **트리플 패턴 강제**
```python
def check_triple_pattern(article_sources: list[dict]) -> dict:
    """3 카테고리 모두 1개 이상 충족 강제:
    - korean_official: language='ko' AND is_official=True (예: 매거진 자체·classmethodkr·KISA·과기정통부)
    - source_official: language='en' AND is_official=True (예: Anthropic News·OpenAI Blog·Google AI Blog)
    - opposing_or_affected: stance='con' OR stance='affected' (예: 반대 관점 분석 또는 영향권자 자료)

    반환: {
        rule: "triple_pattern",
        passed: bool,
        details: {
            korean_official_count: int,
            source_official_count: int,
            opposing_or_affected_count: int,
            missing_categories: List[str],
        },
        recommendation: str,
    }
    """
    ko_official = [s for s in article_sources if s.get("language") == "ko" and s.get("is_official")]
    en_official = [s for s in article_sources if s.get("language") == "en" and s.get("is_official")]
    opposing = [s for s in article_sources if s.get("stance") in ("con", "affected")]

    missing = []
    if len(ko_official) == 0:
        missing.append("korean_official")
    if len(en_official) == 0:
        missing.append("source_official")
    if len(opposing) == 0:
        missing.append("opposing_or_affected")

    return {
        "rule": "triple_pattern",
        "passed": len(missing) == 0,
        "details": {
            "korean_official_count": len(ko_official),
            "source_official_count": len(en_official),
            "opposing_or_affected_count": len(opposing),
            "missing_categories": missing,
        },
        "recommendation": (
            "통과" if not missing
            else f"다음 카테고리 source 추가 필요: {', '.join(missing)}"
        ),
    }
```

### 2. `pipeline/source_registry.py` stance 필드 확장
기존 stance: `pro / neutral / con / unknown` (TASK_019)
추가: `affected` — 영향권자 자료 (예: 사용자 후기·고객 사례·운영자 회고)

`source_registry.py` `update_source` 함수에 stance 새 값 허용:
```python
def update_source(source_id: str, **fields) -> bool:
    valid_stances = {"pro", "neutral", "con", "unknown", "affected"}
    if "stance" in fields and fields["stance"] not in valid_stances:
        raise ValueError(f"잘못된 stance: {fields['stance']} (가능: {valid_stances})")
    ...
```

### 3. `pipeline/source_diversity.py` 5 규칙 통합 검증
기존 `check_diversity()` 함수에 트리플 패턴 추가:
```python
def check_diversity(article_id: str, strict: bool = True) -> dict:
    """5 규칙 통합 검증.

    반환: {
        article_id,
        rules: List[{rule, passed, details}],
        all_passed: bool,
        critical_missing: List[str],
        recommendation: str,
    }
    """
    sources = list_sources(article_id)
    results = [
        check_language_diversity(sources),
        check_stance_diversity(sources),
        check_publisher_diversity(sources),
        check_recency(sources),
        check_triple_pattern(sources),  # 신규
    ]
    all_passed = all(r["passed"] for r in results)
    critical = [r["rule"] for r in results if not r["passed"]]
    ...
```

### 4. publish-gate skill §3 연동
기존 `python pipeline/source_diversity.py --article-id {id} --strict` 명령은 자동으로 5 규칙 검증.

추가 명시:
- 5번째 규칙(트리플 패턴) fail 시 `critical_missing` 카테고리 명시
- 자체 콘텐츠(rights_status: free) 또는 자가 사례 기사는 본 규칙 예외 가능 (편집자 명시 승인 필수)

### 5. 단위 테스트 `tests/test_source_diversity_triple.py`
- `test_triple_pattern_all_present_passes`
- `test_missing_korean_official_fails`
- `test_missing_source_official_fails`
- `test_missing_opposing_fails`
- `test_affected_stance_counts_as_opposing`
- `test_self_content_exception_with_editor_approval`
- `test_5_rules_integrated_check`

### 6. 5월 호 16 꼭지 적용 점검 (수동)
| 꼭지 | KO 공식 | EN 공식 | 반대/영향 | 통과 |
|---|---|---|---|---|
| #1 claude-code-multi-agent | classmethodkr 2건 | Anthropic 1건 | (보강 필요) | 🟡 |
| #2 bedrock-403 | classmethodkr 5건 | AWS docs 1건 | (보강 필요) | 🟡 |
| #6 anthropic-engineering-deep | (보강 필요) | Anthropic 5건 | (보강 필요) | 🔴 |
| ... | | | | |

→ 5/04 plan_issue 시점에 본 표 채우고 부족 source 추가 brief 단계에서 보강.

## 완료 조건

- [ ] `pipeline/source_diversity.py` 5번째 규칙 추가
- [ ] `pipeline/source_registry.py` stance "affected" 값 허용
- [ ] publish-gate skill §3 5 규칙 통합 검증
- [ ] 단위 테스트 7건 pass
- [ ] ruff clean / mojibake clean
- [ ] 5월 호 16 꼭지 트리플 패턴 충족 점검 표 (5/04 plan_issue 시점 업데이트)

## 후속

- TASK_060 (G2 게이트) + TASK_062 (종합 검수) + 본 5번째 규칙 통합 — publish-gate skill 3단계 자동화 강화
- 6월 호부터 본 규칙 의무화 (5월 호는 점진 도입 — 부족 source는 편집자 명시 예외 승인)

## 완료 처리

```bash
python codex_workflow.py update TASK_063 implemented
python codex_workflow.py update TASK_063 merged
```
