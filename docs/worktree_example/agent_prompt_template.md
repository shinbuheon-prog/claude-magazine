# Agent 위임 프롬프트 표준 템플릿

> TASK_031 보강. 재사용 가능한 위임 프롬프트 구조.

---

## 기본 템플릿

```
Claude Magazine 프로젝트의 {TASK_ID} ({태스크 제목})을 구현하는 작업입니다.

## 프로젝트 위치
/c/Users/shin.buheon/claude-magazine

## 먼저 읽어야 할 파일 (순서대로)
1. CLAUDE.md — 코딩 규칙
2. AGENTS.md — 에이전트 행동 규칙
3. tasks/{TASK_ID}.md — 완료 조건 및 구현 명세
4. {의존 모듈 1}
5. {참고 패턴 파일}

## 해야 할 일

### 1. {단계 1 설명}
{구체 지침 + Bash/Python 명령어}

### 2. {단계 2 설명}
...

### N. 스모크 테스트
```bash
cd /c/Users/shin.buheon/claude-magazine
{테스트 명령어}
```

### N+1. 완료 처리
```bash
cd /c/Users/shin.buheon/claude-magazine
python codex_workflow.py update {TASK_ID} implemented
```

## 주의사항
- Windows UTF-8 출력 깨짐 방지 (fact_checker.py 패턴)
- 모든 HTTP 호출 timeout=10
- 기존 시그니처 하위 호환 유지
- **{타 Agent가 병렬로 작업 중인 파일}은 건드리지 말 것**
- API 키 없으면 graceful skip (해당 체크만)

## 완료 후 보고
1. 생성/수정 파일 목록
2. 스모크 테스트 결과
3. 완료 조건 달성 여부
4. codex_workflow.py update 실행 결과
```

---

## 병렬 위임 시 추가 섹션

병렬 위임이면 프롬프트 마지막에 반드시 추가:

```
## 병렬 Agent 알림
이 작업은 다른 Agent와 동시에 진행됩니다.

**건드리지 말 파일 목록** (다른 Agent 영역):
- {파일 경로 1}
- {파일 경로 2}

**공유 파일 수정 시 주의**:
- requirements.txt: 마지막에 1줄 추가 (중간 수정 금지)
- .env.example: 기존 줄 보존하고 하단에 추가
- CODEX_TASKS: 본인 TASK 라인만 수정
```

---

## Agent tool 호출 구조

```javascript
Agent({
  description: "TASK_XXX {짧은 요약}",           // 3-5 단어
  isolation: "worktree",                        // 병렬 위임 시 필수
  subagent_type: "general-purpose",             // 기본 (대부분 이걸로)
  prompt: `{위 템플릿 내용}`,                    // 셀프 컨테인드 (Agent는 이전 대화 모름)
  run_in_background: false                      // true면 완료 시 알림
})
```

### subagent_type 선택 가이드

| 작업 유형 | 추천 subagent_type |
|---|---|
| 일반 구현 | `general-purpose` |
| 코드베이스 탐색·검색 | `Explore` |
| 설계·플랜 수립 | `Plan` |
| Claude Code SDK 질문 | `claude-code-guide` |

---

## 좋은 프롬프트 vs 나쁜 프롬프트

### ❌ 나쁜 예
```
TASK_030 구현해줘. CLAUDE.md 참고.
```
- Agent는 이전 대화 모름 → 컨텍스트 부족
- "참고"는 너무 모호
- 완료 조건·테스트 기준 없음

### ✅ 좋은 예
```
TASK_030 구현 작업. 프로젝트: /c/Users/shin.buheon/claude-magazine

읽을 파일: CLAUDE.md, AGENTS.md, tasks/TASK_030.md, .claude/skills/editorial-review/SKILL.md

해야 할 일:
1. .claude/skills/ 하위에 3개 skill 추가 (brief-generation, pdf-compile, weekly-improvement)
2. 각 SKILL.md는 editorial-review 패턴 따라 frontmatter + 3개 섹션 포함

스모크 테스트:
  python scripts/validate_skills.py
  → 8개 모두 ✅ 확인

완료 처리:
  python codex_workflow.py update TASK_030 implemented

주의: .claude/skills/editorial-review/ 등 기존 5개는 건드리지 말 것.
```

---

## 위임 전 자가 검증 체크리스트

- [ ] description 3-5 단어로 짧고 명확한가?
- [ ] 프롬프트에 프로젝트 경로 명시?
- [ ] 읽어야 할 파일 우선순위 순서로 나열?
- [ ] 단계별 지침 + 구체 명령어 포함?
- [ ] 스모크 테스트 명령어 제공?
- [ ] 완료 처리 명령 (codex_workflow update)?
- [ ] 병렬 위임 시 "건드리지 말 파일" 명시?
- [ ] worktree 격리 필요한지 판단 완료?
- [ ] API 키 없을 때 fallback 경로 명시?

---

## 관련 문서

- [README.md](README.md) — 판단 체크리스트 + 시나리오
- [merge_workflow.md](merge_workflow.md) — 완료 후 머지
