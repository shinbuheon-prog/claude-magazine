---
name: brief-generation
description: 주제 기반 주간 기사 브리프 생성 (소스 수집 → 다양성 검사 → Sonnet 호출 → JSON 브리프). "주간 브리프", "brief generation", "topic 브리프" 트리거.
allowed-tools: Bash, Read, Write
---

# 주간 브리프 생성 (Brief Generation)

## 언제 사용
- 사용자가 "이번 주 {주제}로 브리프 만들어줘" 요청
- `scripts/run_weekly_brief.py --topic` 실행 필요 시
- 월간 콘텐츠 플래닝에서 신규 기사 추가 시

## 절차 (Systematic)

### 1. 주제 확인
- 사용자 메시지에서 TOPIC 추출
- TOPIC이 불명확하면 후보 3개 제시 후 선택 요청

### 2. 소스 묶음 준비
두 경로 중 선택:
- **파일 소스**: `--sources src1.md src2.md ...`
- **source_registry 소스**: article_id 지정 (TASK_004)

### 3. (권장) 소스 다양성 사전 검사
```bash
python pipeline/source_diversity.py --article-id {id}
```
- 4규칙 중 실패 있으면 편집자에게 추가 소스 제안

### 4. 브리프 생성 (Sonnet 4.6)
```bash
python scripts/run_weekly_brief.py \
    --topic "{TOPIC}" \
    --dry-run
```
- `--dry-run`: Ghost 발행 없이 브리프 + 초안까지만
- 산출물: `drafts/brief_YYYYMMDD_HHMMSS.json`, `drafts/draft_YYYYMMDD_HHMMSS.md`

### 5. 브리프 JSON 검증
- 필수 키 7개 존재: `working_title`, `angle`, `why_now`, `outline`, `evidence_map`, `unknowns`, `risk_flags`
- `evidence_map`의 모든 `source_id`가 source_registry에 등록됐는지

### 6. 편집자 보고
- 브리프 파일 경로 + 제목 후보 + 주요 outline 3개 요약

## Verify before success
- [ ] `drafts/brief_*.json` 생성됨
- [ ] 7개 필수 키 전부 존재
- [ ] source_diversity 4규칙 중 최소 3개 통과
- [ ] Sonnet request_id 로그에 기록됨 (`logs/brief_*.json`)

## 비용 참고
- Sonnet 4.6 호출 1회 + Haiku 분류 수회
- 회당 약 $0.15~$0.30

## 관련 스킬
- 이후 단계: editorial-review → publish-gate
- 병행: source-validation
