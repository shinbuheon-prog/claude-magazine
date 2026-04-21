# 팀 협업 가이드

## 브랜치 전략

```
main          ← 배포 가능한 안정 코드 (직접 push 금지)
  └── develop ← 통합 브랜치 (PR 머지 대상)
        ├── task/TASK_001   ← Codex 태스크별 브랜치
        ├── task/TASK_003
        └── article/2026-05-01-claude-sonnet-guide  ← 기사별 브랜치
```

## 작업 시작

```bash
# 최신 develop 기준으로 브랜치 생성
git checkout develop
git pull origin develop
git checkout -b task/TASK_003

# 작업 완료 후
git add .
git commit -m "feat(TASK_003): brief_generator.py 구현"
git push origin task/TASK_003
```

## 커밋 메시지 규칙

```
feat(범위): 새 기능 추가
fix(범위): 버그 수정
chore(범위): 설정·의존성 변경
docs(범위): 문서 수정
style(범위): 포맷·린트만 수정
test(범위): 테스트 추가·수정

예시:
feat(TASK_003): brief_generator.py 스트리밍 구현
fix(source_registry): mark_used 중복 방지 버그 수정
docs(TASK_005): 팩트체크 에이전트 완료 조건 명확화
```

## PR 규칙

1. **PR 대상**: `develop` 브랜치 (main 직접 PR 금지)
2. **PR 템플릿** 체크리스트 전부 완료 후 요청
3. **리뷰어**: 편집장 1인 필수 승인
4. **CI 통과** 필수 (lint + 스모크 테스트)

## Codex 태스크 위임 워크플로우

```
1. GitHub Issue 생성 (ISSUE_TEMPLATE/task.md 사용)
2. 브랜치 생성: git checkout -b task/TASK_XXX
3. tasks/TASK_XXX.md 를 Codex에 전달
4. Codex 구현 완료 → python codex_workflow.py update TASK_XXX implemented
5. PR 생성 → develop 머지
6. python codex_workflow.py update TASK_XXX merged
```

## 기사 작업 워크플로우

```
1. GitHub Issue 생성 (ISSUE_TEMPLATE/article.md 사용)
2. 브랜치 생성: git checkout -b article/YYYY-MM-DD-slug
3. pipeline 실행:
   python scripts/run_weekly_brief.py --topic "TOPIC" --dry-run
4. drafts/ 확인 → 편집자 검수
5. 편집 검수 체크리스트 10개 항목 완료
6. PR 생성 → develop 머지 → 발행
```

## 환경 설정

```bash
# 1. 레포 클론
git clone https://github.com/shinbuheon-prog/claude-magazine.git
cd claude-magazine

# 2. 환경변수 설정
cp .env.example .env
# .env 편집: ANTHROPIC_API_KEY 등 입력

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 보드 확인
python codex_workflow.py list
```

## 민감정보 규칙

- `.env` 는 절대 커밋 금지 (`.gitignore`에 포함됨)
- API 키는 팀 내 안전한 채널(1Password, Slack DM 등)로만 공유
- `logs/`, `data/`, `drafts/` 는 gitignore 대상 (개인 로컬에만)
