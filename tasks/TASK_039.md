# TASK_039 — Claude Code 2.1.x 신기능 통합

## 메타
- **status**: merged
- **prerequisites**: TASK_030, TASK_033, TASK_037
- **실 소요**: ~45분
- **Phase**: 5 확장 (플랫폼 최신 기능 채택)

## 목적
Claude Code v2.1.111~117 릴리즈의 매거진 운영에 즉시 도움 되는 기능을 채택:
- Opus 4.7 **1M 컨텍스트** 복원 (v2.1.117 버그 수정)
- **/ultrareview** 병렬 멀티에이전트 코드 리뷰 (v2.1.111)
- Agent frontmatter **mcpServers** 지원 (v2.1.117)
- Subagent **forking** 확장성 (v2.1.117)
- Opus 4.7 **xhigh** effort 레벨 (v2.1.111)

## 작업 범위 (4 Phase)

### Phase 1 — MCP frontmatter 예시 주석
- 8개 skill SKILL.md에 `mcpServers` 예시 주석 추가
- 실제 MCP 서버 구현은 후속 태스크 (TASK_040+)로 분리
- 활성화 조건·마이그레이션 경로 문서화

### Phase 2 — Opus 1M 컨텍스트 활용 문서
- `docs/claude_code_features.md` 신규 작성
- fact_checker·sop_updater에 1M 권장 시점 주석 추가
- xhigh effort 적용 가이드

### Phase 3 — /ultrareview 통합 문서
- `publish_monthly.py`의 품질 게이트 섹션에 안내
- README에 수동 호출 워크플로우 기록

### Phase 4 — Subagent forking 운영 가이드
- `AGENTS.md` "Worktree 격리 원칙" 섹션 확장
- `CLAUDE_CODE_FORK_SUBAGENT=1` 환경변수 도입 장단점
- worktree + forking 조합 권장 패턴

## 완료 조건
- [ ] 8개 SKILL.md에 mcpServers 예시 주석
- [ ] docs/claude_code_features.md 작성
- [ ] fact_checker.py에 1M·xhigh 주석
- [ ] publish_monthly.py에 /ultrareview 가이드 주석
- [ ] AGENTS.md Subagent forking 섹션 추가
- [ ] CODEX_TASKS TASK_039 merged

## 완료 처리
`python codex_workflow.py update TASK_039 merged`
