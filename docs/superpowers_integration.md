# Superpowers 플러그인 통합 가이드

> obra/superpowers 플러그인을 Claude Magazine 프로젝트와 병행 사용하는 방법.

---

## 현재 상태

프로젝트 내 `.claude/skills/`에 **매거진 전용 8개 skill**이 이미 등록되어 있습니다 (TASK_030 완료).
Superpowers 플러그인은 **선택 사항** — 설치하지 않아도 로컬 skills는 정상 동작합니다.

**언제 Superpowers 플러그인도 함께 설치하면 좋은가**:
- TDD(RED-GREEN-REFACTOR), git worktree 자동화 같은 **범용 개발 방법론**이 필요할 때
- 매거진 외 다른 개발 작업에도 Claude Code를 사용할 때
- 팀 전체가 동일한 개발 워크플로우 표준을 공유해야 할 때

---

## 설치 방법

### Claude Code (권장)

```bash
# Claude Code CLI에서 실행
/plugin install superpowers@claude-plugins-official
```

설치 후 확인:
```bash
/plugin list
# → superpowers가 목록에 표시되면 성공
```

### 기타 도구

| 도구 | 명령어 |
|---|---|
| Cursor | `/add-plugin superpowers` |
| Gemini CLI | `gemini extensions install https://github.com/obra/superpowers` |
| OpenCode | (공식 문서 참조) |
| GitHub Copilot CLI | (공식 문서 참조) |

---

## Superpowers의 7단계 워크플로우

obra/superpowers는 다음 7단계를 강제:

1. **Brainstorming** — 설계 문서 생성 전 아이디어 정제
2. **Git Worktree 활용** — 격리된 개발 환경 구성
3. **Plan 작성** — 2~5분 단위 실행 가능한 작업 분해
4. **Sub-agent 주도 개발** — 독립 에이전트 병렬 작업 + 이단계 검토
5. **TDD (RED-GREEN-REFACTOR)** — 테스트 주도 개발 강제
6. **Code Review 요청** — 계획 준수 여부 점검
7. **개발 브랜치 완료** — merge/PR 결정

---

## 로컬 Skills와의 관계

### 역할 분담

| 영역 | 담당 |
|---|---|
| **매거진 업무 자동화** | 로컬 `.claude/skills/` (프로젝트 전용) |
| **범용 개발 방법론** | Superpowers 플러그인 (전역) |

### 중복 영역

두 체계가 겹치는 부분:
- **Verify before success** — 로컬 Skills도 이미 채택 (TASK_030 원칙)
- **Sub-agent 분산** — 로컬 AGENTS.md에도 정의됨 (TASK_031)
- **Git worktree** — 로컬 AGENTS.md + docs/worktree_example/ 완성됨

→ **로컬 Skills 8개로 매거진 업무는 충분**. Superpowers는 그 위 상위 방법론.

---

## 병행 사용 패턴

### 패턴 1: 매거진 업무만 (Superpowers 미설치)

```
사용자: "이번 주 Claude 4 브리프 만들어줘"
↓
Claude Code: brief-generation skill 자동 호출
↓
run_weekly_brief.py 실행 + 검증 + 보고
```

**장점**: 단순, 즉시 동작  
**단점**: 범용 방법론 부재

### 패턴 2: Superpowers + 로컬 Skills (권장)

```
사용자: "TASK_032 기능 추가해줘"
↓
Superpowers: brainstorming → plan → worktree → TDD
              ↓ (구현 단계에서)
로컬 Skills: editorial-review 등 매거진 업무 자동화
              ↓
Superpowers: code review → merge
```

**장점**: 체계적 + 도메인 특화  
**단점**: 학습 곡선, 두 체계 이해 필요

### 패턴 3: 로컬 Skills 우선, Superpowers는 의식적 호출

```
사용자: "이 리팩토링에 TDD 적용해서 해줘"
↓
Claude Code: Superpowers TDD 워크플로우 호출
↓
로컬 Skills는 필요 시 보조 역할
```

**장점**: 유연함  
**단점**: 일관성 다소 낮음

---

## 설치 확인

Superpowers 설치 후 다음으로 확인:

```bash
# Claude Code에서
/skills list
```

출력 예시:
```
매거진 전용 (로컬):
  - editorial-review
  - fact-check-cycle
  - ...

Superpowers (플러그인):
  - brainstorming
  - worktree-dev
  - tdd-cycle
  - ...
```

---

## 비교 표

| 항목 | 로컬 Skills | Superpowers |
|---|---|---|
| 범위 | 프로젝트 전용 | 전역 |
| 도메인 | 매거진 출판 | 일반 소프트웨어 개발 |
| 설치 | 자동 (repo 포함) | 수동 (`/plugin install`) |
| 관리 | 프로젝트 팀 | obra + 커뮤니티 |
| 업데이트 | git pull | `/plugin update` |
| 의존성 | 매거진 pipeline | 없음 (독립) |
| 수 | 8개 | 다수 (7단계 + 보조) |

---

## FAQ

### Q: Superpowers를 설치하면 로컬 Skills가 덮어씌워지나요?
A: 아니오. 로컬 `.claude/skills/`는 프로젝트 전용 공간이고, Superpowers는 사용자 전역 설정에 들어갑니다. 충돌 없이 공존.

### Q: Superpowers 없이도 모든 기능이 동작하나요?
A: 네. 매거진 업무는 로컬 8개 skill로 완결됩니다. Superpowers는 "상위 방법론" 레이어.

### Q: 프로젝트 새 멤버에게 Superpowers 설치를 요구해야 하나요?
A: 선택 사항. 매거진 기여만 목적이면 불필요. 대규모 기능 개발 참여면 권장.

### Q: 로컬 Skills의 자동 트리거 키워드가 Superpowers와 겹치면?
A: Claude Code가 description 유사도로 판단. 애매하면 사용자에게 선택 질문.

---

## 참고 링크

- obra/superpowers: https://github.com/obra/superpowers
- 공식 마켓플레이스: claude-plugins-official
- 로컬 Skills 가이드: [../.claude/skills/](../.claude/skills/)
- Worktree 실전 가이드: [worktree_example/](worktree_example/)
