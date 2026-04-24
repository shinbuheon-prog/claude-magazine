# Git Worktree 기반 Agent 병렬 위임 — 실전 가이드

> TASK_031 보강 문서. AGENTS.md의 "Worktree 격리 원칙"의 실전 적용 예시.

---

## 왜 worktree인가

**문제 시나리오** (worktree 없이 병렬 위임):
```
Agent A: App.jsx 수정 (TASK_030)  ─┐
                                     ├── 동시 발생 → 충돌
Agent B: App.jsx 수정 (TASK_031)  ─┘
```

**해결** (worktree 격리):
```
main branch ─── Agent A (agent-a-branch, 별도 디렉토리) ─── merge
             └─ Agent B (agent-b-branch, 별도 디렉토리) ─── merge
```

각 Agent가 **독립된 작업 디렉토리**에서 작업 → 파일 잠금·충돌 없음.

---

## 3가지 실전 시나리오

### 시나리오 1: 완전 독립 파일 (worktree 불필요)

**상황**: TASK_021 (CoverPage.jsx + covers/) + TASK_022 (App.jsx + 3 새 컴포넌트)

**판단**:
- TASK_021: `web/public/covers/`, `web/src/components/CoverPage.jsx`
- TASK_022: `web/src/App.jsx`, `web/src/components/InterviewPage.jsx` 등
- 공유 파일: 없음 (겹치는 파일 0개)

**결론**: worktree 불필요. 대신 각 Agent에게 **"상대 영역 건드리지 말 것"** 명시.

**위임 패턴**:
```
Agent A 프롬프트에 추가:
  "## 주의사항
   - **App.jsx는 건드리지 말 것** (다른 Agent가 병렬로 수정 중)"

Agent B 프롬프트에 추가:
  "## 주의사항
   - **web/public/covers/ 및 CoverPage.jsx는 건드리지 말 것**"
```

---

### 시나리오 2: 공유 파일 있음 (worktree 강력 권장)

**상황**: TASK_016·017·018·019 4개 병렬 (전부 pipeline/ 수정)

**판단**:
- 공유 파일: `requirements.txt`, `.gitignore`, `CODEX_TASKS`
- 각 Agent가 requirements.txt에 패키지 추가 시도 → 같은 줄 충돌 가능

**결론**: worktree 격리 사용.

**위임 패턴** (Agent tool 호출):
```
Agent({
  description: "TASK_016 편집 체크리스트 위임",
  isolation: "worktree",    ← 핵심
  prompt: "..."
})
```

완료 후:
1. 각 Agent는 별도 브랜치에 커밋 (예: `agent-a31c96614ba5784c3`)
2. main에 순차 머지: `git merge --no-ff {agent-branch}`
3. `requirements.txt` 충돌 있으면 수동 해결

---

### 시나리오 3: 대규모 리팩토링 (worktree 필수)

**상황**: 가상 — pipeline/ 전체를 `src/pipeline/`로 이동 + import 경로 일괄 수정

**판단**:
- 모든 Python 파일 수정
- 단일 Agent로도 가능하지만 시간 오래 걸림
- 분할 병렬 위임이 효율적

**결론**: **반드시 worktree**. 공유 파일 100% 겹침.

**위임 패턴**:
```
# 3개 Agent 분할 병렬
Agent A: pipeline/{brief,draft,fact,channel}_*.py 이동
Agent B: pipeline/{source,editor,ghost,disclosure}_*.py 이동
Agent C: scripts/ 내 import 경로 일괄 업데이트

각각 isolation: "worktree" 지정
```

완료 후: 순차 머지 + 통합 테스트.

---

## 판단 체크리스트

| 질문 | Yes | No |
|---|---|---|
| 2개 이상 Agent 병렬? | 다음 질문 | worktree 불필요 |
| 공유 파일 수정 가능성? | worktree 사용 | 파일 명시로 충분 |
| 10+ 파일 편집? | worktree 필수 | 공유 파일만 주의 |
| 대규모 리팩토링? | worktree 필수 | - |

---

## 머지 워크플로우

1. **Agent 완료 알림 확인**
   - 각 Agent는 `agentId: aXXXX` 제공
   - 변경사항은 `agent-{id}` 브랜치에 자동 커밋됨

2. **브랜치 확인**
   ```bash
   git branch -a | grep agent-
   ```

3. **순차 머지** (충돌 최소화 위해 작은 변경부터)
   ```bash
   git checkout develop
   git merge --no-ff agent-a31c96614ba5784c3 -m "merge: TASK_016 agent"
   git merge --no-ff agent-a6306cc1b505222cf -m "merge: TASK_017 agent"
   ```

4. **충돌 해결** (예: requirements.txt)
   ```bash
   # 충돌 파일 확인
   git status
   # 수동 편집 (중복 제거)
   git add requirements.txt
   git commit
   ```

5. **통합 스모크 테스트**
   ```bash
   python scripts/test_e2e.py        # mock 전 경로 검증
   python scripts/check_env.py       # 환경변수 검증
   python scripts/validate_skills.py # Skills 검증
   ```

6. **Push**
   ```bash
   git push origin develop
   ```

---

## 관련 문서

- [AGENTS.md](../../AGENTS.md) — Worktree 격리 원칙 정식 규정
- [agent_prompt_template.md](agent_prompt_template.md) — 표준 위임 프롬프트
- [merge_workflow.md](merge_workflow.md) — 머지 상세 절차
