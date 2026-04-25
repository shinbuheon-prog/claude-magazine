# Release v0.2.1 — GitHub Release 등록용 노트

**태그**: `v0.2.1`
**커밋**: `08ccfff` (main HEAD, Phase 8 closure + Cowork integration merge)
**릴리즈 제목**: `v0.2.1 — Phase 8 closure + Cowork integration`

---

## 등록 절차

### 방법 1: GitHub Web UI (권장)
1. https://github.com/shinbuheon-prog/claude-magazine/releases/new
2. **Tag** 드롭다운에서 `v0.2.1` 선택
3. **Release title**: `v0.2.1 — Phase 8 closure + Cowork integration`
4. **Previous tag** = `v0.2.0` 선택 → **Generate release notes** 클릭 (자동 commit 요약)
5. **Description** 자동 생성된 노트 **위쪽**에 아래 "Release body" 섹션 붙여넣기
6. (선택) `output/claude-magazine-2026-05.pdf` 또는 `claude-magazine-2026-04.pdf` 첨부
7. **Set as the latest release** 체크 (자동 활성)
8. **Publish release** 클릭

### 방법 2: gh CLI
```bash
gh release create v0.2.1 \
  --title "v0.2.1 — Phase 8 closure + Cowork integration" \
  --notes-file reports/release_v0.2.1_notes.md \
  --latest
```

---

## Release body (Description 필드에 복사·붙여넣기)

```markdown
v0.2.0 이후 12 commits — Phase 8(자율성 강화) 종결 + Cowork × Drive 통합 + 운영 도구 추가.

## 🎯 하이라이트

### Phase 8 종결 — 자율 개선 폐쇄 루프
- **TASK_053 머지** — `weekly_improvement` 루프가 cache·citations·illustration·publish 4 운영 신호 소비
- **TASK_054 머지** — 반복 실패 자동 감지 + `weekly_improvement` 우선순위 큐 (3회+ 같은 failure_class)
- **failure_repeat_detector Slack 실시간 알림** — 큐 마커 작성 시 즉시 통보

### Cowork × Drive 통합 (시나리오 B — 연계)
- `docs/integrations/cowork_project_context.md` — Cowork 프로젝트 지침 (붙여넣기 가능)
- `docs/integrations/cowork_drive_integration.md` — 시스템 아키텍처
- `docs/integrations/sns_to_magazine_pipeline.md` — 편집자 운영 SOP
- `reports/monthly_digest_2026-04-W3.md` — 시범 큐레이션 1회분 (5 클러스터 + 5 갭 영역)

### 운영 도구
- `scripts/audit_budget.py` — illustration 월간 예산 감시 CLI
  - 무료 발행 원칙(`MONTHLY_USD_CAP=0.0` 기본값)을 기술적으로 강제
  - `--strict`로 cap 초과 시 exit 1, `--notify`로 80%+ Slack 알림
  - 16 tests, 89% coverage

### 안정화
- **codex_sync.yml 첫 green** — v0.1.0 이후 매 push마다 실패하던 워크플로우, 3건 수정으로 복구
  - `*_draft.md` 제외 (정식 task와 ID 충돌 방지)
  - skip-if-no-change (timestamp-only 변경 시 commit 생성 안 함)
  - `permissions: contents: write` 선언
- **pytest 49 → 97** (+48 신규) — failure_collector·failure_repeat_detector·sop_updater·audit_budget 4 모듈 ≥70% 커버리지

## 📊 지표 (2026-04-26 기준)

| 지표 | 값 |
|---|---|
| 머지 태스크 | 53 (TASK_001~054, TASK_020 cancelled) |
| pytest | 97/97 통과 |
| ruff | 0 issues |
| CI job | 7개 병렬, main green |
| codex_sync | green (v0.1.0 이후 첫 성공) |
| cache 히트율 | 45.9% (실측) |
| editorial_lint 커버리지 | 85% |
| citations_store 커버리지 | 90% |

## 🔒 운영 정책 유지

- 무료 발행 원칙 (결제 기능 없음, TASK_020 cancelled)
- LLM 비용 0 (Agent SDK Max 구독 경유, TASK_033)
- 이미지 기본 경로 Pollinations (무료, TASK_047)
- 월간 illustration 비용 상한 env=0.0 (`audit_budget.py --strict`로 강제)

## 🔄 Upgrade Notes (v0.2.0 → v0.2.1)

**Breaking 없음.** 기존 운영자 별도 migration 불필요.

새로 활용 가능한 기능:
- `python scripts/audit_budget.py --strict` (cron 또는 CI 통합 권장)
- Cowork 프로젝트 컨텍스트 (`docs/integrations/cowork_project_context.md` 붙여넣기)
- 주간 디제스트 SOP (`docs/integrations/sns_to_magazine_pipeline.md`)
- 시범 큐레이션 1회분 (`reports/monthly_digest_2026-04-W3.md`)

## 🤝 협업 모델

매거진은 **Claude Code (오케스트레이터) + Codex (서브에이전트) + 편집자 (인간)** 3자 협업으로 개발됩니다.
v0.2.1에서는 추가로 **Cowork (자동화 매개)** 가 통합되어 4자 모델로 확장:

```
Cowork ─→ Drive 데이터 분석·디제스트 자동 생성
   ↓
Claude Code ─→ 매거진 콘텐츠 파이프라인·코드 리뷰
   ↓
Codex ─→ TASK_*.md 단위 구현 위임
   ↓
편집자 (인간) ─→ Gate 1·Gate 2 승인 + 모든 발행 결정
```

전체 변경 내역은 [CHANGELOG.md](https://github.com/shinbuheon-prog/claude-magazine/blob/main/CHANGELOG.md) 참조.
```

---

## Attach binaries 후보

- `output/claude-magazine-2026-05.pdf` (1.6 MB) — 5월 매거진 샘플
- `output/claude-magazine-2026-04.pdf` (2.4 MB) — 4월 매거진 샘플

첨부 권장 — 독자·기여자가 즉시 매거진 톤·품질 확인 가능.

---

## v0.2.0 별도 등록 여부

**비권장 (선택)** — v0.2.1이 latest이고 v0.2.0의 가치를 모두 포함. 깔끔한 Release 페이지를 위해 v0.2.1만 단독 등록 권장.

만약 v0.2.0도 별도 등록하려면:
- 새 New release → tag `v0.2.0` 선택 → [reports/release_v0.2.0_notes.md](release_v0.2.0_notes.md)의 "Release body" 섹션 붙여넣기
- 단, "Set as the latest release" 체크 해제 — v0.2.1을 latest로 유지

---

## 변경 이력

- 2026-04-26: 초안 작성. v0.2.0 → v0.2.1 12 commits 정리.
