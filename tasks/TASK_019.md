# TASK_019 — 소스 다양성 규칙 엔진 (source_diversity.py)

## 메타
- **status**: todo
- **prerequisites**: TASK_004
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요
- **Phase**: 3 (팩트체크 품질 레버)

---

## 목적
브리프 생성 전 `source_bundle`이 충분히 다양한 관점을 포함하는지 자동 검사.
리포트 인용: _"한국어 공식 문서 1개 이상 + 영문 공식 문서 1개 이상 + 반대 관점 또는 영향권 외 자료 1개 이상. 편향·게이 리스크 완화."_

---

## 구현 명세

### 생성할 파일: `pipeline/source_diversity.py`

### CLI
```bash
# 기사별 소스 묶음 검사
python pipeline/source_diversity.py --article-id art-001

# 소스 파일 경로 직접 지정
python pipeline/source_diversity.py --sources src1.md src2.md src3.md

# 실패해도 경고만 (기본: --strict 아니면 통과)
python pipeline/source_diversity.py --article-id art-001 --strict
```

### 다양성 규칙 (4개 체크)

| # | 규칙 | 판정 | 실패 시 메시지 |
|---|---|---|---|
| 1 | 언어 다양성 | 한국어 공식 1+ AND 영문 공식 1+ | "한국어 공식 출처 없음" / "영문 공식 출처 없음" |
| 2 | 관점 다양성 | 찬성·중립·반대 중 2개 이상 카테고리 포함 | "모든 소스가 동일 관점 (찬성)" |
| 3 | 발행처 집중도 | 단일 publisher 비중 ≤ 60% | "publisher 'X'가 전체 소스의 83% 차지" |
| 4 | 시효성 | 최신 소스 1개 이상 (30일 이내) AND 배경 소스 1개 이상 (365일 초과 OK) | "30일 이내 소스 없음 — 시의성 부족" |

### source_registry 스키마 확장
기존 `source_registry.py`의 `sources` 테이블에 다음 필드 추가 (migration 필요):
```sql
ALTER TABLE sources ADD COLUMN language TEXT DEFAULT 'unknown';
  -- 'ko' | 'en' | 'ja' | 'zh' | ...
ALTER TABLE sources ADD COLUMN stance TEXT DEFAULT 'neutral';
  -- 'pro' | 'neutral' | 'con' | 'unknown'
ALTER TABLE sources ADD COLUMN is_official INTEGER DEFAULT 0;
  -- 0 | 1 (정부·학술·공식 기관 여부)
```

### stance 판정 (자동)
- source 등록 시 Haiku 4.5로 "이 문서는 주제에 대해 찬성/중립/반대 중 어느 관점인가?" 분류 호출
- 분류 결과를 `stance` 컬럼에 저장
- 수동 override 가능 (`python pipeline/source_registry.py update SRC_ID --stance con`)

### 함수 시그니처
```python
def check_diversity(article_id: str) -> dict:
    """
    source_registry에서 article_id 소스 조회 → 4개 규칙 검사.
    반환: {
        "passed": bool,
        "rules": [
            {"id": "language", "status": "pass|fail", "detail": "..."},
            ...
        ],
        "summary": "모든 규칙 통과" | "N개 규칙 실패",
        "recommendations": ["영문 공식 출처 1개 이상 추가 필요", ...]
    }
    """

def classify_stance(source_text: str, topic: str) -> str:
    """Haiku 호출로 pro/neutral/con/unknown 분류"""
```

### 출력 형식
```
=== 소스 다양성 검사 ===
article_id: art-001
총 소스: 7개

[1/4] 언어 다양성
  ✅ 한국어 공식: 3개 (과기정통부, 개인정보위, 한국저작권위)
  ✅ 영문 공식: 2개 (Anthropic, OpenAI)

[2/4] 관점 다양성
  ⚠️  pro: 4개, neutral: 3개, con: 0개
     → 반대 관점 소스 1개 이상 추가 권장

[3/4] 발행처 집중도
  ✅ 최대 집중: Anthropic 29% (2/7)

[4/4] 시효성
  ✅ 30일 이내: 3개
  ✅ 배경(365일+): 2개

=== 결과: 3 통과 / 1 경고 ===
권고: 반대 관점 소스 1개 이상 추가 (경고만 — 발행 차단 아님)
```

### 브리프 생성 통합
`brief_generator.py`에서 호출 패턴:
```python
from pipeline.source_diversity import check_diversity

def generate_brief(topic, article_id, sources):
    diversity = check_diversity(article_id)
    if not diversity["passed"]:
        print("⚠️  소스 다양성 부족:", diversity["summary"])
        if args.strict:
            sys.exit(1)
    # 기존 로직 계속...
```

---

## 완료 조건
- [ ] `pipeline/source_diversity.py` 생성
- [ ] 4개 규칙 전부 구현
- [ ] `source_registry` 스키마에 language, stance, is_official 컬럼 추가 (migration)
- [ ] `classify_stance()` Haiku 호출 구현
- [ ] `brief_generator.py`에 `check_diversity()` 호출 삽입 (경고 출력)
- [ ] 스모크 테스트: 가짜 article_id로 4개 규칙 동작 확인
- [ ] 기존 sources 테이블 데이터 손실 없이 migration 완료

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_019 implemented
```
