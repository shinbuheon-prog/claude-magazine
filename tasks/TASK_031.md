# TASK_031 — Git Worktree 기반 Agent 병렬 위임 표준화

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요
- **Phase**: 5 (Superpowers 철학 적용)

---

## 목적
obra/superpowers 원칙: **Git worktree로 병렬 작업 격리**.
현재 Agent 병렬 위임 시 동일 디렉토리에서 작업 → 파일 충돌 리스크.
worktree 격리를 표준으로 채택해 N개 Agent가 안전하게 병렬 작업.

---

## 구현 명세

### 1. AGENTS.md 업데이트
**병렬 실행 가능한 태스크 조합** 섹션 아래에 "Worktree 격리 원칙" 추가:

```markdown
## Worktree 격리 원칙 (TASK_031)

**병렬 Agent 위임 시 필수**: 각 Agent는 별도 git worktree에서 작업해 파일 충돌 방지.

### 언제 worktree 격리 필요
- 2개 이상 Agent가 병렬로 동일 저장소 수정 시
- 특히 App.jsx·pipeline/__init__.py 같은 공유 파일 편집 가능성 있을 때

### 언제 불필요
- 단일 Agent 작업
- Agent가 서로 완전히 다른 폴더만 건드릴 때 (예: web/ vs pipeline/)
- 빠른 수정·문서만 변경

### Worktree 사용 패턴
Claude Code Agent 호출 시:
- isolation: "worktree" 옵션 지정
- Agent 완료 시 변경사항은 사람이 리뷰·머지

### 머지 워크플로우
1. Agent 완료 → 별도 브랜치에 커밋됨
2. 메인 브랜치로 merge (git merge --no-ff 권장)
3. 충돌 시 편집자 수동 해결
```

### 2. 태스크 명세 템플릿 업데이트
기존 `tasks/TASK_*.md`의 **메타** 섹션에 추가 필드:

```markdown
- **서브에이전트 분할**: 가능 (A: ... / B: ...)
- **Worktree 격리 권장**: 예 (병렬 위임 시)
```

새로 작성되는 태스크는 이 필드를 기본으로 포함.

### 3. 표준 위임 프롬프트 스니펫
위임 시 재사용 가능한 체크리스트 (AGENTS.md에 포함):

```markdown
## 병렬 Agent 위임 표준 체크리스트

위임 전:
- [ ] 동일 파일 충돌 가능성 분석
- [ ] 2개 이상 병렬 시 isolation: "worktree" 지정
- [ ] 각 Agent에게 "건드리지 말 파일" 명시

위임 프롬프트 공통 항목:
- 읽어야 할 파일 순서
- 수정 금지 파일 목록
- 스모크 테스트 명령어
- 완료 처리 명령어 (codex_workflow update)

완료 후:
- [ ] 각 Agent의 변경사항 검증
- [ ] 충돌 있으면 수동 해결
- [ ] 통합 스모크 테스트
```

### 4. 실제 활용 사례 문서
TASK_021·022가 동시 위임될 때 이미 충돌 방지 가이드 있었음 — 이를 표준 패턴으로 승격:

```markdown
### 사례: TASK_021 + TASK_022 병렬 위임
- TASK_021: web/public/covers/ + CoverPage.jsx
- TASK_022: App.jsx + 신규 3 컴포넌트
- 공유 파일 충돌: 없음 (다른 파일)
- worktree 격리: 불필요 (단, Agent에게 상호 수정 금지 명시)
```

---

## 완료 조건
- [ ] `AGENTS.md`에 "Worktree 격리 원칙" 섹션 추가
- [ ] 병렬 위임 표준 체크리스트 문서화
- [ ] 기존 태스크 명세 템플릿에 "Worktree 격리 권장" 필드 추가 안내
- [ ] 실제 활용 사례 (TASK_021+022, TASK_013+014+015 등) 기록
- [ ] 머지 워크플로우 명시
- [ ] 향후 신규 태스크 작성 시 이 표준 자동 적용됨

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_031 implemented
```

## 주의사항
- 이 태스크는 **문서 업데이트만** — 실제 코드 변경 없음
- Worktree는 Claude Code harness 기능 (별도 설정 불필요)
- Windows에서 worktree 경로 길이 제한 주의
- worktree는 자동 정리됨 (변경 없으면)
