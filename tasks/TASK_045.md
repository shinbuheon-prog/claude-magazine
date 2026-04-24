# TASK_045 — Citations API 이중 운영 도입 (source-id 체크 보강)

## 메타
- **status**: todo
- **prerequisites**: TASK_005 (fact_checker), TASK_016 (editorial_lint source-id 체크), TASK_025 (article_standards Pass/Fail)
- **예상 소요**: 120~150분
- **서브에이전트 분할**: 가능 (Phase 2 vs Phase 3 병렬)
- **Phase**: 5 확장 (출처 신뢰도 강화)

---

## 목적
[anthropics/claude-cookbooks](https://github.com/anthropics/claude-cookbooks) **Citations** 레시피 도입.
Anthropic Citations API는 Claude가 응답 중 인용 영역을 **문서 좌표(문장/문단 인덱스)로 자동 표기**. 매거진 현재는 수동 `source_id` 연결 방식.

**도입 방향**: 기존 방식과 **이중 운영** — Citations API 결과를 별도 레이어로 저장해 **수동 source_id 체크와 교차 검증**. 기존 방식 대체 아님.

---

## 현재 상태 vs 도입 후

### 현재 (수동 source-id)
```
fact_checker.py → 판정 표 (| 문장 | 판정 | 근거 source_id | ... |)
editorial_lint.py source-id 체크 → 본문 문장에 source_id 링크 검증
```
문제점:
- source_id 누락 감지는 되나 **위치(어느 출처의 어느 문단)는 수동 확인**
- 편집자가 원문 대조 필요

### 도입 후 (Citations API 병행)
```
fact_checker.py → [A] 기존 판정 표 (기존 유지)
              └→ [B] Citations API 결과 → citations JSON (신규)

editorial_lint.py source-id 체크 → 
  - 기존: source_id 존재 여부만
  - 신규: Citations와 수동 source_id **일치 여부** 교차 검증 (불일치 = warn)
```

---

## 구현 명세

### Phase 1: fact_checker.py에 Citations API 레이어 추가 (60분)

#### 1.1 API 변경
현재 `messages.stream(system=..., messages=...)` → Citations API는 document content block 필요:
```python
messages=[{
    "role": "user",
    "content": [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": source_text},
            "title": "Source 1",
            "citations": {"enabled": True},
        },
        # 다른 출처들...
        {"type": "text", "text": "draft 검증 요청..."},
    ],
}]
```

#### 1.2 출처 매핑
`source_registry`의 source_id와 Citations API의 document index 매핑 테이블 관리:
```python
document_map = [
    {"doc_index": 0, "source_id": "SRC_001", "url": "..."},
    {"doc_index": 1, "source_id": "SRC_002", "url": "..."},
]
```

#### 1.3 응답 저장
`data/citations.db` 또는 `data/citations/<article_id>.json` 신규:
```json
{
  "article_id": "ARTICLE_001",
  "claims": [
    {
      "claim_idx": 0,
      "text": "...",
      "citations": [
        {"source_id": "SRC_001", "char_start": 120, "char_end": 180, "quote": "..."}
      ]
    }
  ]
}
```

#### 1.4 모델 배치
- Opus 4.7 유지 (fact_checker 기존 모델, CLAUDE.md 규칙)

---

### Phase 2: editorial_lint.py 교차 검증 체크 추가 (40분)

#### 2.1 신규 체크 `citations-cross-check`
- 기존 `source-id` 체크와 **별개 체크**로 추가 (기존 유지)
- 판정:
  - `pass` — 수동 source_id와 Citations API 결과가 **동일 출처 지시**
  - `warn` — Citations API 결과 없음 (레거시 기사)
  - `fail` — 수동 source_id와 Citations API **지시 출처가 다름**

#### 2.2 report 스키마 확장
기존 `{id, status, message, details}` 구조 유지, `citations-cross-check` 추가.

#### 2.3 `--mode article`에만 추가
TASK_041에서 `--mode card-news` 신설됨. 본 체크는 **article 모드 전용**.

---

### Phase 3: spec/article_standards.yml 업데이트 (15분)

```yaml
source_quality:
  must_pass:
    # 기존
    - id: "source_id_coverage"
      ...
    # 신규
    - id: "citations_consistency"
      rule: "Citations API 결과가 수동 source_id와 일치"
      measure: "citations-cross-check pass"
      severity: "warn"  # fail 아닌 warn으로 시작 (이중 운영 초기)
```

**이유**: 이중 운영 초기에는 fail로 두면 기존 발행 기사가 자동 재검증 불가 상태 — `warn`으로 시작해 데이터 축적 후 승격 여부 결정.

---

### Phase 4: 비용·호출 구조 측정 (15분)
- Citations API는 일반 Messages API 대비 **document 토큰 수 증가** (원문 전체 포함)
- 월간 80p 21꼭지 × 기사당 평균 5 출처 × 원문 평균 크기 측정
- TASK_044 Prompt Caching 적용 후 Citations과 조합 시 실제 비용 산출
- `reports/task045_citations_cost.md`에 기록

---

## 중요 전제 (TASK_044와 동일)

**Agent SDK(Max 구독) 경로 vs API 직접 경로 구분**:
- Citations API는 **API 직접 호출 전용 기능** (SDK 지원 여부 재확인 필요)
- Phase 1.1에서 `CLAUDE_PROVIDER` 분기 처리:
  - `api`: Citations 사용
  - `sdk`: 기존 방식 유지 (Citations 건너뜀, 로그에 skip 기록)
  - `mock`: 고정 응답

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| Citations API가 SDK 경로에서 미지원 | Phase 1에서 `CLAUDE_PROVIDER=sdk`는 skip + 로그 기록. 기존 동작 회귀 없음 |
| 원문 전체 전송으로 토큰 비용 급증 | Phase 4 비용 측정 필수, TASK_044 Prompt Caching과 결합 권장 |
| 수동 source_id와 Citations API 결과 **초기 불일치율 높음** | severity=`warn`으로 시작, 점진적 승격. 초기 2주 데이터 축적 후 `fail` 전환 여부 판단 |
| 장문 출처(논문 PDF 등)에서 Citations 좌표 부정확 | `char_start/char_end`와 `quote` 둘 다 저장해 교차 검증 가능 |
| 기존 `fact_checker.py` 판정 표 포맷 변경 | 판정 표는 **그대로 유지** (편집자 읽기 호환성), Citations는 **별도 JSON 레이어** |

---

## 무료 발행 원칙 정합성
- Citations API 자체는 일반 Messages API와 동일 과금
- 원문 토큰 증가로 호출당 비용 상승 가능 → TASK_044 캐싱으로 상쇄 권장
- Phase 4 측정 결과가 월 운영 한도(편집자 개인 부담 수준)를 초과하면 **도입 보류**, backlog로 전환

---

## 완료 조건 (Definition of Done)
- [ ] `fact_checker.py`에 Citations API 호출 경로 추가 (기존 판정 표 유지)
- [ ] CLAUDE_PROVIDER 분기: api=사용, sdk=skip 기록, mock=고정
- [ ] `data/citations/<article_id>.json` (또는 DB) 저장 구조 동작
- [ ] source_registry source_id ↔ Citations document_index 매핑 로직
- [ ] `editorial_lint.py --mode article`에 `citations-cross-check` 체크 추가
- [ ] `spec/article_standards.yml`에 `citations_consistency` 항목 추가 (severity=warn)
- [ ] 기존 `source-id` 체크 회귀 없음
- [ ] 스모크: 테스트 기사 3건으로 Citations 레이어 생성 + 교차 검증 pass/warn/fail 각 케이스 확인
- [ ] `reports/task045_citations_cost.md` 월간 예상 비용 기록
- [ ] `reports/task045_citations_smoke_<date>.md` 실제 호출 결과 요약

---

## 산출물
- `pipeline/fact_checker.py` (Citations 레이어 추가)
- `pipeline/editorial_lint.py` (`citations-cross-check` 신규)
- `pipeline/citations_store.py` (신규, citations 저장·조회 헬퍼)
- `data/citations/` (신규 디렉터리, gitignore)
- `spec/article_standards.yml` (`citations_consistency` 추가)
- `reports/task045_citations_cost.md` (신규)
- `reports/task045_citations_smoke_<date>.md` (신규)

---

## 후속 태스크 후보
- **TASK_047 후보**: severity=warn → fail 승격 (2주 데이터 축적 후 불일치율 <5% 시)
- **TASK_048 후보**: 편집자 UI(TASK_029)에 Citations 시각화 — 인용 좌표 하이라이트

---

## 완료 처리
```bash
python codex_workflow.py update TASK_045 implemented
python codex_workflow.py update TASK_045 merged
```
