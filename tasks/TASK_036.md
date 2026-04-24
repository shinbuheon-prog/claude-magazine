# TASK_036 — 월간 플랜 관리 CLI

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 50분
- **Phase**: 5 확장 (운영 효율)

## 목적
21꼭지 월간 매거진의 진행 상황을 **YAML 매니페스트**로 관리.
편집자가 CLI 한 줄로 호 초기화·꼭지 추가·상태 조회 가능.

## 구현 명세

### 생성 파일
```
scripts/
└── plan_issue.py

drafts/
└── issues/
    ├── .gitkeep
    └── (2026-05.yml 등 월별 이슈 플랜 생성됨)
```

### YAML 스키마 (`drafts/issues/YYYY-MM.yml`)
```yaml
issue: 2026-05
theme: "에이전트 시대의 실무 전환"
editor_in_chief: "편집장 이름"
created_at: "2026-04-22T10:00:00+09:00"

articles:
  - slug: agent-economics
    category: feature          # cover·feature·deep_dive·insight·interview·review
    title_draft: "AI 에이전트 경제학"
    assignee: editor-A
    source_ids: [src-001, src-002]
    target_pages: 14
    status: planning           # planning|brief|draft|fact_check|lint|approved|published
    brief_path: ""
    draft_path: ""
    ghost_post_id: ""

sections_order:                # 목차 섹션 순서
  - feature
  - deep_dive
  - insight
  - interview
  - review
```

### CLI 서브커맨드
```bash
# 새 호 초기화
python scripts/plan_issue.py init --month 2026-05 --theme "에이전트 시대의 실무 전환"

# 꼭지 추가
python scripts/plan_issue.py add-article --month 2026-05 --slug agent-economics \
    --category feature --title "AI 에이전트 경제학" --pages 14

# 상태 업데이트
python scripts/plan_issue.py update-status --month 2026-05 --slug agent-economics \
    --status draft

# 진행 현황 (전체 꼭지 + 상태별 카운트)
python scripts/plan_issue.py status --month 2026-05

# 이슈 목록
python scripts/plan_issue.py list

# 플랜 유효성 검증
python scripts/plan_issue.py validate --month 2026-05
```

### 상태 전이 검증
- `planning → brief → draft → fact_check → lint → approved → published`
- 역전이(backward) 허용 (편집자가 수동 복귀 가능)
- 순방향 스킵 경고만, 차단 안 함

### 출력 예시 (`status`)
```
=== 2026-05 "에이전트 시대의 실무 전환" ===
편집장: 편집장 이름
생성일: 2026-04-22

꼭지 21개:
  ✅ 발행 완료    2  (published)
  🟢 승인 대기    5  (approved)
  🟡 lint 진행   3  (lint)
  🟠 팩트체크    4  (fact_check)
  🔵 초안 작성   4  (draft)
  ⚪ 브리프      2  (brief)
  ⬜ 기획        1  (planning)

진행률: 9.5% (2/21 published)
```

## 완료 조건
- [ ] `scripts/plan_issue.py` 생성 (6개 서브커맨드)
- [ ] YAML 스키마 검증 로직
- [ ] 상태 전이 검증
- [ ] 스모크 테스트: init → add-article × 3 → status 확인

## 완료 처리
`python codex_workflow.py update TASK_036 merged`
