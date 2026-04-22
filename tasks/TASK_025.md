# TASK_025 — 기사 이상 상태(Pass/Fail) 스펙 시스템

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 60분
- **서브에이전트 분할**: 불필요
- **Phase**: 4 (의도 기반 엔지니어링)

---

## 목적
Miessler "Intent-Based Engineering" 원칙 적용.
**기사 카테고리별 "이상 상태"를 정량 pass/fail 기준으로 정의**해 모든 품질 파이프라인이 일관된 기준으로 판정하게 한다.

리포트 인용: _"8~12 단어 binary pass/fail 기준이 새로운 엔지니어링 기술. 이상 상태를 정의할 수 있는 사람이 거대한 이점을 획득."_

---

## 구현 명세

### 1. 생성 파일
```
spec/
├── article_standards.yml        ← 카테고리별 pass/fail 기준
└── README.md                     ← 스펙 편집 가이드
pipeline/
└── standards_checker.py          ← 스펙 로드 + 검증 엔진
scripts/
└── validate_standards.py         ← YAML 스키마 검증
```

### 2. `spec/article_standards.yml` 구조

```yaml
# 공통 기준 (모든 카테고리에 적용)
common:
  must_pass:
    - id: "source-id-coverage"
      rule: "모든 주장 문장에 source_id 연결"
      measure: "100%"
    - id: "ai-disclosure"
      rule: "AI 사용 고지 문구 존재"
      measure: "presence"
    - id: "correction-policy"
      rule: "정정 책임자 + 24시간 기한 명시"
      measure: "presence"

# 카테고리별 추가 기준
categories:
  interview:
    must_pass:
      - id: "direct-quotes"
        rule: "직접 인용 8개 이상"
        measure: "count >= 8"
      - id: "follow-up-questions"
        rule: "주요 질문 5개 모두 후속 질문 포함"
        measure: "follow_up_ratio == 1.0"
      - id: "editor-notes-limit"
        rule: "편집자 주 3개 이하, 각 40단어 이하"
        measure: "count <= 3 AND max_words <= 40"
    should_pass:
      - id: "subject-portrait"
        rule: "인터뷰이 사진 1장 이상"

  deep_dive:
    must_pass:
      - id: "source-count"
        rule: "source 10개 이상"
        measure: "count >= 10"
      - id: "source-language-mix"
        rule: "한국어·영문 공식 소스 각 3개 이상"
        measure: "ko_official >= 3 AND en_official >= 3"
      - id: "quantitative-claims"
        rule: "정량 수치 5개 이상, 모두 source_id 연결"
        measure: "count >= 5 AND sourced_ratio == 1.0"
      - id: "counter-perspective"
        rule: "반대 관점 섹션 1개 이상"
        measure: "has_con_section"

  review:
    must_pass:
      - id: "criteria-scored"
        rule: "평가 기준 3개 이상 점수화"
        measure: "count >= 3"
      - id: "pros-cons-balance"
        rule: "Pros·Cons 각 2개 이상"
        measure: "pros >= 2 AND cons >= 2"
      - id: "competitor-comparison"
        rule: "경쟁 제품 1개 이상 비교"
        measure: "competitor_count >= 1"

  feature:
    must_pass:
      - id: "word-count-range"
        rule: "본문 1500~4000 단어"
        measure: "1500 <= words <= 4000"
      - id: "pull-quote-count"
        rule: "pull quote 2개 이상"
        measure: "count >= 2"
      - id: "section-count"
        rule: "섹션 4개 이상"
        measure: "count >= 4"

  insight:
    must_pass:
      - id: "data-chart"
        rule: "차트 1개 이상 + 출처 명시"
        measure: "has_chart AND chart_source_id"
      - id: "trend-direction"
        rule: "증감 방향 명시 (상승·하락·횡보 중 하나)"
        measure: "presence"

  brief:
    must_pass:
      - id: "word-count-range"
        rule: "본문 400~900 단어"
        measure: "400 <= words <= 900"
      - id: "key-takeaway"
        rule: "핵심 요점 3개 명시"
        measure: "count == 3"
```

### 3. `pipeline/standards_checker.py` 시그니처

```python
def load_standards(path: str = "spec/article_standards.yml") -> dict:
    """YAML 로드 + 스키마 검증"""

def check_article(
    draft_path: str,
    category: str,
    metadata: dict | None = None,
) -> dict:
    """
    반환: {
        "category": str,
        "common_checks": [{"id", "rule", "status", "measured", "expected"}...],
        "category_checks": [...],
        "must_pass_total": int,
        "must_pass_passed": int,
        "should_pass_total": int,
        "should_pass_passed": int,
        "can_publish": bool,
    }
    """

def measure_metric(rule_id: str, text: str, metadata: dict) -> dict:
    """각 rule의 measure 필드를 평가 — 측정값 반환"""
```

### 4. CLI
```bash
# 카테고리 지정 + 검사
python pipeline/standards_checker.py --draft article.md --category deep_dive

# 스펙 검증만 (초안 없이)
python scripts/validate_standards.py spec/article_standards.yml

# 모든 카테고리 요약
python pipeline/standards_checker.py --list-categories
```

### 5. 측정 엔진 분류 (measure 필드)

| 패턴 | 예시 | 구현 |
|---|---|---|
| 단순 카운트 | `count >= 8` | 정규식 카운트 후 비교 |
| 비율 | `follow_up_ratio == 1.0` | 특수 로직 (질문-후속 매칭) |
| 존재 | `presence` | 키워드/태그 존재 여부 |
| 언어별 | `ko_official >= 3` | source_registry 조회 |
| 단어 수 | `1500 <= words <= 4000` | 마크다운 파싱 후 단어 카운트 |
| 복합 | `count >= 5 AND sourced_ratio == 1.0` | AND/OR 파서 |

### 6. editorial_lint.py 통합
기존 `editorial_lint.py`에 신규 체크 항목 추가:
```python
# editorial_lint의 10개 체크 + standards_checker 결과를 통합 리포트로
```

---

## 완료 조건
- [ ] `spec/article_standards.yml` 생성 (6개 카테고리: interview·deep_dive·review·feature·insight·brief)
- [ ] `spec/README.md` 스펙 편집 가이드
- [ ] `pipeline/standards_checker.py` 구현
- [ ] `scripts/validate_standards.py` YAML 스키마 검증
- [ ] measure 필드 6가지 패턴 전부 지원
- [ ] `editorial_lint.py`에 standards_checker 통합 (선택)
- [ ] 스모크 테스트: 각 카테고리 샘플 draft로 검증 → pass/fail 판정 정확
- [ ] YAML 수정 시 `validate_standards.py`가 스키마 오류 검출

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_025 implemented
```

## 주의사항
- YAML 로딩은 `PyYAML` 사용 (requirements.txt 확인)
- measure 필드는 eval 아닌 파서로 구현 (보안)
- 스펙 파일 수정은 git 이력 추적 — 과거 기준 비교 가능
