---
name: fact-check-cycle
description: 팩트체크 → 수정 필요 문장 추출 → 재작성 → 재팩트체크 루프. "팩트체크 루프", "fact check cycle" 등에 트리거.
allowed-tools: Bash, Read, Edit
---

# 팩트체크 사이클 (Fact-Check Cycle)

## 언제 사용
- 사용자가 "팩트체크 루프 돌려줘", "fact check cycle" 요청
- 기사 품질 향상을 위한 반복 검증 요청
- 초기 팩트체크 결과의 "수정 필요" 항목이 3건 이상일 때

## 절차 (Systematic)

### 1. 초기 팩트체크
```bash
python pipeline/fact_checker.py --draft {draft_path} --article-id {article_id}
```
- 결과 마크다운 표에서 "수정 필요" 또는 "과장됨" 문장 추출

### 2. 수정 필요 시 (자동 재작성)
- 각 "수정 필요" 문장에 대해 `draft_writer.py`로 재작성 요청
- 편집자가 승인한 수정안만 draft에 반영 (자동 수정 금지)
- 편집자 판정을 `editor_corrections.py`에 기록:
```bash
python pipeline/editor_corrections.py add \
    --article-id {id} --category {cat} \
    --type factual --original "..." --corrected "..." --severity high
```

### 3. 재팩트체크
```bash
python pipeline/fact_checker.py --draft {수정된_draft_path} --article-id {article_id}
```

### 4. 종료 조건
- 전체 위험도 "낮음" 또는 "중간" 도달
- 또는 최대 2회 반복 (무한 루프 방지)
- 3회 반복에도 "높음"이면 편집자 수동 개입 요청

## Verify before success
- [ ] 최종 팩트체크 결과 "낮음" 또는 "중간"
- [ ] 수정된 모든 문장이 source_id와 일치
- [ ] editor_corrections.db에 판정 기록됨 (severity high 이상)
- [ ] logs/factcheck_*.json에 request_id 기록됨

## 주의
- Opus 4.7 호출 비용 발생 (팩트체크는 Opus 사용)
- 재작성은 Sonnet 4.6 사용 (비용 균형)
- 자동 수정 절대 금지 — 편집자 승인 필수

## 관련 스킬
- 후속 발행 준비: publish-gate
- 소스 다양성 확보: source-validation
