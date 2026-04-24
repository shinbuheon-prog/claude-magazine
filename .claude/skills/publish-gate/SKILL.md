---
name: publish-gate
description: editorial_lint + standards_checker + source_diversity 통합 게이트 + AI 고지 삽입. "발행 준비", "publish gate", "게시 전 검증"에 트리거.
allowed-tools: Bash, Read, Edit
---

# 발행 게이트 (Publish Gate)

## 언제 사용
- 사용자가 "발행 준비해줘", "publish gate", "게시 전 검증" 요청
- 기사 발행 직전 종합 검증 필요
- Ghost draft가 published로 전환되기 직전

## 절차 (Systematic — 순서 엄수)

### 1. editorial_lint (10개 체크) — strict
```bash
python pipeline/editorial_lint.py --draft {draft_path} --strict --json
```
- 실패 시 **즉시 중단** + 실패 항목 보고
- can_publish: false면 절대 다음 단계 진행 금지

### 2. standards_checker (카테고리별 기준)
```bash
python pipeline/standards_checker.py --draft {draft_path} --category {category}
```
- category는 interview/deep_dive/review/feature/insight/brief 중 하나
- must_pass 전부 통과 필수, should_pass는 경고

### 3. source_diversity (4규칙)
```bash
python pipeline/source_diversity.py --article-id {article_id} --strict
```
- 4규칙 전부 통과 또는 편집자 명시적 예외 승인

### 4. AI 사용 고지 삽입
- 기사 카테고리에 맞는 템플릿 선택:
  - 단순 기사 → light
  - 심층 리포트 → heavy (사용 모델 명시)
  - 인터뷰 → interview
```bash
python pipeline/disclosure_injector.py --html {html_path} --template {heavy|light|interview}
```
- 또는 Ghost 포스트 직접 업데이트:
```bash
python pipeline/disclosure_injector.py --ghost-post-id {id} --template heavy
```

### 5. 최종 승인 준비 메시지
```
✅ 발행 게이트 전부 통과
  - editorial_lint: 10/10
  - standards_checker: {must_pass_passed}/{must_pass_total}
  - source_diversity: 4/4
  - AI 고지: v1.0 삽입 완료

다음 단계:
  - Ghost draft 상태 확인
  - 편집자 최종 승인 후 status=published 전환
  - 또는 editor_api_server.py의 승인 UI 사용
```

## Verify before success
- [ ] 3단계 모두 strict 통과 (또는 예외 승인)
- [ ] disclosure 삽입 확인 (data-version 태그 존재)
- [ ] 편집자에게 다음 액션 명확 전달
- [ ] 실패 시 어느 단계에서 중단됐는지 명시

## 주의
- **자동 발행 금지** — 이 skill은 검증 + 고지 삽입까지만
- 실제 `status=published` 전환은 사람이 수행
- 게이트 실패는 모두 로그로 남김 (logs/publish_gate_*.json)

## 관련 스킬
- 개별 검증: editorial-review, source-validation
- 팩트체크 심화: fact-check-cycle
- 발행 후 배포: sns-distribution
