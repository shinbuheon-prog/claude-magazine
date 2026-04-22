---
name: editorial-review
description: 매거진 기사 draft의 발행 전 10개 체크 자동 실행. "기사 검토", "editorial review", "draft 검수" 등에 트리거.
allowed-tools: Bash, Read, Grep
---

# 편집 검토 (Editorial Review)

## 언제 사용
- 사용자가 "기사 검토해줘", "editorial review", "이 draft 검수해줘" 요청
- `drafts/` 폴더의 Markdown 파일 경로가 언급됨
- Ghost 포스트 ID가 언급되며 검토 요청

## 절차 (Systematic)

### 1. draft 경로 확인
- 사용자 요청에서 파일 경로 또는 Ghost post id 추출
- 파일이 존재하지 않으면 즉시 중단 + 경로 확인 요청

### 2. editorial_lint 실행
```bash
python pipeline/editorial_lint.py --draft {draft_path} --json
```
- `--ghost-post-id` 지정 시 `--draft` 대신 ghost post id 사용

### 3. 결과 해석
- JSON 응답의 `items[]` 배열에서 `status: "fail"` 항목 추출
- 실패 항목별 `message` 요약 보고
- `can_publish: false`면 발행 불가 상태 명시

### 4. 수정 제안 (실패 항목에 대해)
- `source-id` 실패 → 어느 문장에 source 필요한지 제안
- `ai-disclosure` 실패 → disclosure_injector.py 안내
- `quote-fidelity` 실패 → 원문 대조 위치 안내
- `pii-check` 실패 → pii_masker.py 안내

## Verify before success
- [ ] editorial_lint.py 실행 성공 (exit 0 또는 1)
- [ ] 10개 체크 항목 전부 실행됨 (items[] 길이 == 10)
- [ ] 실패 항목별 수정 제안 제공됨
- [ ] 사용자에게 `can_publish` 상태 명확히 전달됨

## 관련 스킬
- 최종 발행 준비: publish-gate
- AI 고지 삽입: disclosure 생성 (수동)
