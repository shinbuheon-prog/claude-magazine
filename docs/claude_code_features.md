# Claude Code 2.1.x 신기능 활용 가이드 (TASK_039)

> Claude Code v2.1.111~117 릴리즈 중 매거진 운영에 즉시 유용한 기능만 선별 정리.

---

## 🎯 핵심 요약

| 기능 | 버전 | 매거진 활용 |
|---|---|---|
| **Opus 4.7 1M 컨텍스트 복원** | v2.1.117 | 장문 특집 + 소스 일괄 팩트체크·자율 개선 루프 |
| **/ultrareview** 병렬 리뷰 | v2.1.111 | 월간 21꼭지 병렬 품질 게이트 |
| **Opus 4.7 xhigh** effort | v2.1.111 | 핵심 꼭지 품질 튜닝 |
| **Subagent forking** | v2.1.117 | 병렬 Agent 위임 안정성 |
| **Agent frontmatter mcpServers** | v2.1.117 | (향후 MCP 서버 구현 후 활성화) |

---

## 1️⃣ Opus 4.7 1M 컨텍스트

### 변경 사항
- v2.1.117에서 Opus 4.7의 컨텍스트 창 **200K → 1M 복원** (이전 버그 수정)
- 1회 호출로 대용량 자료 분석 가능

### 매거진 활용 시점

**A. `fact_checker` — 장문 특집 1회 검증**
```python
# pipeline/fact_checker.py
# Feature(14p) + 소스 묶음 15~20개 + editor_heuristics = 약 80K~150K tokens
# 1M 컨텍스트 이내 충분 → 이전처럼 섹션별 분할 불필요
```

권장 시나리오:
- FeaturePage (14p) 전체 + 관련 소스 20개 + heuristics를 **단일 호출**로 팩트체크
- 이전: 섹션 4~5개로 쪼개 호출 (re-context 비용)
- 이후: 한 번에 일관성 있는 판정

**B. `sop_updater` — 30일치 실패 데이터 일괄 분석**
```python
# pipeline/sop_updater.py (TASK_027)
# 30일 editor_corrections + editorial_lint 실패 + reports → 500K tokens 가능
# 1M 창으로 패턴 간섭·장기 트렌드 추출 개선
```

월간 마감 직후 실행 권장:
```bash
CLAUDE_PROVIDER=sdk python scripts/weekly_improvement.py --since-days 30
```

### 주의
- Max 구독에서 1M 컨텍스트 세션 1회는 세션 한도의 상당 부분 소비
- 월 5시간 세션 × 4회 리셋 기준으로 **월 4~8회 권장**
- 일반 검토는 여전히 Sonnet 4.6 (200K) 사용

---

## 2️⃣ /ultrareview — 병렬 멀티에이전트 코드 리뷰

### 기능
- 클라우드 병렬 에이전트가 같은 코드·문서를 **동시에 여러 관점으로 검토**
- PR 번호 인자 지원: `/ultrareview 42`
- 현재 브랜치 전체 검토: `/ultrareview`

### 매거진 활용

**Week 3 품질 게이트 가속**

현재 `publish_monthly.py`의 **Stage 2**는 꼭지별 직렬 검사:
```
21 꼭지 × (lint + standards + diversity) = 평균 15~20분
```

`/ultrareview`로 바꾸면:
```
21 꼭지 병렬 리뷰 (클라우드 멀티에이전트) = 평균 3~5분
```

### 권장 워크플로우
```bash
# 1. 플랜 꼭지 전체를 develop 브랜치에 push
git add drafts/ && git commit -m "drafts: 2026-05 호 초안 준비"
git push origin develop

# 2. Claude Code에서 수동 호출
/ultrareview

# 3. 리뷰 결과 확인 후 꼭지별 status 업데이트
python scripts/plan_issue.py update-status --month 2026-05 --slug X --status approved
```

### 주의
- `/ultrareview`는 **코드 중심** 설계 — 매거진 원고(Markdown)도 작동하지만 editorial_lint·standards_checker와 역할 상이
- 품질 게이트의 **보완**이지 **대체**가 아님
- 병렬 리뷰 결과는 사람이 최종 선별 필수

---

## 3️⃣ Opus 4.7 xhigh effort

### 레벨 체계
```
low → medium → high → xhigh → max
```
- `xhigh`는 **high와 max 사이**, 비용 효율 좋은 최상위 추론

### 매거진 활용

**Cover Story 특집·월간 개선 리포트 같은 핵심 꼭지**
```bash
# fact_checker CLI에 effort 전달 (수동 설정, TASK_040 후보)
# 현재 구조에선 API 파라미터로 전달되지 않음 — Claude Code 세션 내 /effort 로 전환
```

권장:
- 일반 브리프·초안: **medium** (기본)
- 팩트체크: **high**
- Cover Story 최종 검토: **xhigh** (Claude Code 세션 `/effort xhigh` 선언 후 실행)
- 월간 sop_updater: **xhigh** (주간 개선 루프 특별 판본)

---

## 4️⃣ Subagent Forking

### 환경변수
```bash
export CLAUDE_CODE_FORK_SUBAGENT=1
```

### 효과
- Agent tool 병렬 위임 시 **각 서브에이전트가 독립 fork**
- 기존: 부모 세션의 상태 공유 → 간섭 가능성
- 이후: 완전 격리, 병렬 안정성 향상

### 매거진 활용
**TASK_031 Worktree 격리와 조합**

```bash
# 21꼭지 병렬 제작 시 (이론적 최대 효율)
export CLAUDE_CODE_FORK_SUBAGENT=1

# 각 Agent 호출에 isolation: "worktree" 지정
# → 파일 격리 + 세션 격리 이중 보호
```

### 주의
- Max 구독 세션 한도 내에서 여전히 제약
- 8~10개 병렬이 현실적 상한 (5시간 리셋 기준)
- 기능 플래그 단계적 롤아웃 — 안정화 확인 후 운영 반영 권장

---

## 5️⃣ Agent frontmatter mcpServers (향후 활용)

### 현재 상태
**미활용**. 이유:
- 우리 파이프라인 모듈은 아직 MCP 서버로 노출되지 않음
- skill에 mcpServers 지정해도 로드할 서버 부재
- 잘못된 frontmatter는 skill 실행 자체를 실패시킬 위험

### 향후 활성화 조건 (TASK_040 후보)
1. `pipeline/source_registry.py --mcp-mode` 구현 (MCP stdio 서버)
2. `pipeline/editor_corrections.py --mcp-mode` 구현
3. `pipeline/standards_checker.py --mcp-mode` 구현
4. 각 skill SKILL.md에 mcpServers 블록 추가
5. 실제 호출 시 bash 폴백 → MCP 우선

### 활성화 후 예상 효과
- "기사 검토해줘" 자연어 요청 시 MCP로 source_registry 자동 질의
- bash subprocess 오버헤드 제거 → 응답 속도 향상
- Windows/Linux 일관된 호출 경로

---

## 📋 적용 우선순위

| 순위 | 기능 | 즉시 적용 가능 |
|---|---|---|
| 1 | Opus 1M 컨텍스트 활용 | ✅ (주석만 추가) |
| 2 | /ultrareview 워크플로우 기록 | ✅ (가이드만 추가) |
| 3 | Subagent forking 가이드 | ✅ (AGENTS.md 업데이트) |
| 4 | xhigh effort | ✅ (Claude Code 세션에서 수동) |
| 5 | mcpServers frontmatter | ❌ (MCP 서버 구현 선행 필요) |

---

## 🔗 관련 문서
- [AGENTS.md](../AGENTS.md) — Worktree 격리 원칙 + Subagent forking
- [monthly_magazine_workflow.md](monthly_magazine_workflow.md) — 월간 발행 매뉴얼
- [tasks/TASK_039.md](../tasks/TASK_039.md) — 본 태스크 명세
- [tasks/TASK_033.md](../tasks/TASK_033.md) — Agent SDK 통합 (Max 구독 경유)

## 참고
- [Claude Code Releases](https://github.com/anthropics/claude-code/releases)
- 분석 시점: 2026-04-22 (Claude Code v2.1.117 기준)
