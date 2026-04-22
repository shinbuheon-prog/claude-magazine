# Agent 완료 후 머지 워크플로우

> TASK_031 보강. worktree에서 작업한 Agent 결과를 main/develop에 머지하는 절차.

---

## 단일 Agent 머지 (worktree 없이)

가장 간단한 경우. Agent가 현 디렉토리에서 직접 수정.

```bash
# 1. 변경 확인
git status
git diff

# 2. 스모크 테스트
python scripts/test_e2e.py
python scripts/validate_skills.py

# 3. CODEX_TASKS 상태 업데이트 (implemented → merged)
# CODEX_TASKS 파일 편집 또는:
python codex_workflow.py update TASK_XXX merged

# 4. 커밋 + Push
git add -A
git commit -m "feat: TASK_XXX merge — ..."
git push origin develop
```

---

## 병렬 Agent 머지 (worktree 격리)

Claude Code의 `isolation: "worktree"` 사용 시 자동 처리.

### 자동 동작
1. Agent 시작 시 → 새 worktree 생성 (`~/.claude/worktrees/agent-{id}`)
2. Agent가 해당 worktree에서 작업
3. Agent 완료 시 → 변경사항을 해당 브랜치에 커밋
4. Agent가 변경 없이 완료하면 worktree 자동 제거

### 머지 절차

**1단계: 변경 확인**
```bash
git branch -a | grep agent-
# 출력 예:
#   agent-a31c96614ba5784c3
#   agent-a6306cc1b505222cf
```

**2단계: 브랜치별 변경 리뷰**
```bash
git log agent-a31c96614ba5784c3 --oneline -5
git diff develop..agent-a31c96614ba5784c3
```

**3단계: 순차 머지 (작은 변경부터)**
```bash
git checkout develop
git pull origin develop

# 첫 번째 Agent 머지
git merge --no-ff agent-a31c96614ba5784c3 \
    -m "merge: TASK_016 — editorial_lint.py 구현"

# 두 번째 Agent 머지
git merge --no-ff agent-a6306cc1b505222cf \
    -m "merge: TASK_017 — pii_masker.py 구현"
```

**4단계: 충돌 해결 (발생 시)**

가장 빈번한 충돌 파일 3종:

#### requirements.txt 충돌
```
<<<<<<< HEAD
PyJWT>=2.8.0
PyYAML>=6.0
=======
PyJWT>=2.8.0
Pillow>=10.0.0
>>>>>>> agent-a6306cc1b505222cf
```
**해결**: 양쪽 패키지 모두 유지
```
PyJWT>=2.8.0
PyYAML>=6.0
Pillow>=10.0.0
```

#### CODEX_TASKS 충돌
```
<<<<<<< HEAD
TASK_016 | ... | implemented
=======
TASK_016 | ... | merged
>>>>>>> agent-branch
```
**해결**: Agent가 implemented로 변경 → 사람이 merged로 승격하는 게 정상. `merged` 채택.

#### .env.example 충돌
**해결**: 두 Agent가 각각 다른 환경변수 추가한 경우, 양쪽 다 유지하고 섹션 헤더로 구분.

**5단계: 통합 스모크 테스트**
```bash
# E2E 테스트 (mock)
python scripts/test_e2e.py

# 환경 체크
python scripts/check_env.py

# Skills 검증
python scripts/validate_skills.py

# 각 태스크별 개별 테스트
python pipeline/editorial_lint.py --draft /tmp/test.md
python pipeline/pii_masker.py --input /tmp/test.md --detect-only
# ...
```

**6단계: CODEX_TASKS 최종 업데이트**
```bash
# 각 TASK 상태를 merged로 변경
# (Agent가 implemented로 남겨둔 것을 승격)
```

**7단계: Push**
```bash
git push origin develop
```

---

## worktree 정리

변경이 없는 worktree는 자동 제거되지만, 수동 정리도 가능:

```bash
# 목록
git worktree list

# 특정 worktree 제거
git worktree remove ~/.claude/worktrees/agent-XXX

# 정리 (더 이상 존재하지 않는 것들)
git worktree prune
```

---

## Agent 브랜치 정리

머지 완료된 Agent 브랜치는 삭제:

```bash
# 로컬 브랜치 삭제
git branch -d agent-a31c96614ba5784c3
git branch -d agent-a6306cc1b505222cf

# 원격까지 push된 경우 (보통 Agent는 로컬만)
# git push origin --delete agent-a31c96614ba5784c3
```

---

## 문제 해결

### "refusing to merge unrelated histories"
Agent가 fresh 상태에서 시작한 경우 발생. 드물지만:
```bash
git merge --allow-unrelated-histories agent-XXX
```

### Agent worktree 경로 에러 (Windows)
경로 길이 260자 제한:
```bash
git config --global core.longpaths true
```

### 머지 후 이상 동작
롤백:
```bash
git reset --hard HEAD^1  # 마지막 머지 취소
# 또는 특정 커밋으로
git reset --hard {커밋_해시}
```

---

## 성공 지표

머지 완료 후 확인:

- [ ] `git log --oneline -5`에 머지 커밋 포함
- [ ] `git status` clean
- [ ] 스모크 테스트 전부 통과
- [ ] CODEX_TASKS 모든 관련 TASK `merged` 상태
- [ ] `git push origin develop` 성공

---

## 관련 문서

- [README.md](README.md) — Worktree 판단 체크리스트
- [agent_prompt_template.md](agent_prompt_template.md) — 위임 프롬프트 표준
- [../../AGENTS.md](../../AGENTS.md) — Worktree 격리 원칙
