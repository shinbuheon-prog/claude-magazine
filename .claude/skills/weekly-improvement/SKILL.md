---
name: weekly-improvement
description: 자율 개선 루프 실행 — 실패 패턴 수집 → Sonnet 분석 → SOP 업데이트 제안서 생성. "주간 개선", "weekly improvement", "자율 개선" 트리거.
allowed-tools: Bash, Read
---

# 주간 개선 루프 (Weekly Improvement)

## 언제 사용
- 매주 일요일 23:00 KST 자동 실행 (n8n workflow_5)
- 편집자가 "이번 주 개선 제안 받아봐" 요청
- 품질 지표 이상 감지 시 수동 트리거

## 절차 (Systematic)

### 1. 실패 수집 기간 확인
- 기본 7일, 사용자 지정 시 `--since-days N`
- 14일 이상은 패턴 정확도 상승하지만 비용·시간 증가

### 2. 실패 데이터 수집 (Claude 호출 없음)
```bash
python scripts/weekly_improvement.py --dry-run --since-days 7
```
- 5개 소스 통합: editorial_lint·standards_checker·editor_corrections·Langfuse·Ghost
- 예상 실패 건수 편집자에게 보고

### 3. Sonnet 4.6 분석 + 제안 생성
```bash
python scripts/weekly_improvement.py --since-days 7 \
    --output reports/improvement_$(date +%Y-%m-%d).md
```
- Sonnet 호출: input ~30K tokens, output ~5K tokens
- 회당 비용 ~$0.17 (주 1회 기준 월 $0.66)
- 예상 시간: 30~60초

### 4. 리포트 섹션 확인
생성된 `reports/improvement_*.md`에 다음 섹션 존재:
- 요약 (발행 수·실패 카운트)
- 반복 패턴 N건
- 제안된 업데이트 (git diff 형식)
- 사람 승인 체크리스트

### 5. GitHub Issue 자동 생성 (옵션)
```bash
python scripts/weekly_improvement.py --since-days 7 --create-issue
```
- gh CLI 필요
- issue 본문에 제안서 내용 붙여넣음

### 6. 사람 승인 워크플로우
편집자에게 안내:
1. `git checkout -b improvement-$(date +%Y-%m-%d)`
2. 리포트의 제안 diff를 `git apply` 또는 수동 적용
3. 변경사항 테스트 (스모크 테스트 실행)
4. PR 생성

## Verify before success
- [ ] `reports/improvement_YYYY-MM-DD.md` 생성됨
- [ ] 요약·패턴·제안·체크리스트 4개 섹션 모두 존재
- [ ] Sonnet `request_id`가 `logs/sop_update_*.json`에 기록됨
- [ ] 제안된 diff가 `git apply --check` 통과 가능한 형식
- [ ] PII 미포함 (API key·편집자 이메일 등)

## 비용·제약
- Sonnet 호출 1회 (주 $0.17 내외)
- Opus 대비 40% 비용 절감 (분석용엔 Sonnet 충분)
- 실제 파일 수정 절대 없음 — 제안만

## 관련 스킬
- 편집자 판정 수집: (TASK_026 editor_corrections 참고)
- 성능 대시보드: (TASK_028 metrics_collector 참고)
