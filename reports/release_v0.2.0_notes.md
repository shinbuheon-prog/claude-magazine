# Release v0.2.0 — GitHub Release 등록용 노트

**태그**: `v0.2.0`
**커밋**: 2dfa147 (main HEAD, codex_sync 안정화 포함)
**릴리즈 제목 후보**: `v0.2.0 — Phase 3~7 완결 (39 tasks)`

---

## 릴리즈 등록 절차

### 방법 1: GitHub Web UI (권장)
1. https://github.com/shinbuheon-prog/claude-magazine/releases/new 접속
2. **Choose a tag** 드롭다운에서 `v0.2.0` 선택 (이미 push됨)
3. **Release title**: `v0.2.0 — Phase 3~7 완결 (39 tasks)`
4. **Describe this release**: 아래 "Release body" 섹션 내용 붙여넣기
5. (선택) **Set as the latest release** 체크
6. (선택) `output/claude-magazine-2026-05.pdf`를 **Attach binaries**로 첨부
7. **Publish release** 클릭

### 방법 2: gh CLI (설치 시)
```bash
gh release create v0.2.0 \
  --title "v0.2.0 — Phase 3~7 완결 (39 tasks)" \
  --notes-file reports/release_v0.2.0_notes.md \
  --latest
```

---

## Release body (복사해서 붙여넣기)

```markdown
매거진 발행 체계의 품질·거버넌스·관측·자동화를 대폭 강화한 두 번째 공식 릴리즈입니다.

v0.1.0(2026-04-21) 이후 **39개 태스크 머지**, **7 phase 완결**, **GitHub Actions CI 7 job 병렬 자동 검증 체계 구축**.

## 🎯 하이라이트

### 효율
- **Prompt Caching** 도입 → 입력 토큰 **99% 감소** (620→6), cache 히트율 **45.9%** 실측 (TASK_044)
- **Agent SDK Max 구독 경유**로 LLM API 비용 **$0** 유지 (TASK_033)
- **이미지 생성 무료 경로** 기본값 Pollinations.ai (TASK_047)

### 품질
- **Citations API 이중 운영** — Anthropic 공식 Citations + 수동 source_id 교차 검증 (TASK_045)
- **editorial_lint 15 체크** (article 11 + card-news 4) + pytest 커버리지 85%/90% (TASK_049)
- **기사 이상 상태 Pass/Fail 스펙 시스템** (TASK_025)

### 운영
- **운영 투명성 대시보드** + cache·citations·illustration 위젯 (TASK_028·TASK_048)
- **월간 발행 원스톱** + `--status`·`--reset-stage`·`--from-stage` UX + 텔레메트리 (TASK_037·TASK_050)
- **발행 실패 복구 플레이북** — 7 stage × 14 failure class 자동 가이드 생성 (TASK_051)

### 자동화
- **GitHub Actions CI 7 job 병렬** (lint·smoke·tests·build·env·spec·mojibake) (TASK_052)
- **80페이지 월간 PDF 컴파일러** + Puppeteer 파이프라인 (TASK_035)
- **SNS 카드뉴스 제작** + 밀도 게이트 + 7 레이아웃 (TASK_041)

### 설계
- **Superpowers 철학** — Claude Code Skills 5종 + Git Worktree 병렬 위임 (TASK_030·031)
- **외부 스킬 선별 도입** — baoyu-skills 4종 wrapper (TASK_040)
- **Figma 무료 REST 연동** — paste package 하이브리드 자동화 (TASK_046)

## 📦 Phase 완료 매트릭스

| Phase | 태스크 | 주제 |
|---|---|---|
| 3 | TASK_016~024 | 품질·법적 리스크·디자인 (TASK_020 cancelled) |
| 4 | TASK_025~029 | Miessler AI 원칙 (Pass/Fail·Expertise Diffusion·Autonomous Optimization·Transparency) |
| 5 | TASK_030~039 | Superpowers + 80페이지 발행 체계 |
| 5 확장 | TASK_040~047 | 외부 스킬 + API 효율화 + 무료 이미지 backend |
| 6 | TASK_048~049 | 운영 관측 + 엔지니어링 성숙도 |
| 7 | TASK_050~052 | 발행 신뢰성·배포 자동화 |

## 📊 지표 (2026-04-24 기준)

| 지표 | 값 |
|---|---|
| 머지 태스크 | 50개 (TASK_001~052, 020 cancelled) |
| pytest | 38/38 통과 |
| 커버리지 | editorial_lint 85%, citations_store 90% |
| CI job | 7개 병렬 |
| cache 히트율 | 45.9% (실측) |
| 입력 토큰 절감 | 99% (fact_checker 재실행 시) |

## 🔒 운영 정책

- **무료 발행 원칙 유지** — 결제 기능 없음, PortOne(TASK_020) 도입 취소
- **LLM 비용 0** — Agent SDK Max 구독 경유
- **이미지 기본 경로** Pollinations.ai (인증 불필요·무료)
- **월간 illustration 비용 상한** env로 기술적 차단 (기본값 $0)

## 🔄 변경 로그

전체 내역은 [CHANGELOG.md](https://github.com/shinbuheon-prog/claude-magazine/blob/main/CHANGELOG.md#v020--2026-04-24) 참조.

## ⚠️ Upgrade Notes (v0.1.0 → v0.2.0)

### Breaking 없음
기존 v0.1.0 운영자는 별도 migration 불필요.

### 새 환경변수 (선택)
- `CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER=pollinations` (기본값, 무료)
- `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=0.0` (기본 0.0 — 유료 provider 자동 차단)
- `HUGGINGFACE_TOKEN` (선택, 고품질 이미지)
- `FIGMA_ACCESS_TOKEN` + `FIGMA_FILE_KEY` (선택, SNS 자산 연동)

### 새 의존성
- `pytest>=8.0` + `pytest-cov>=5.0` (`requirements-dev.txt`)
- 기존 `requirements.txt`는 변경 없음

### CI 세팅
GitHub Actions 7 job이 자동 활성화. main 브랜치 보호 규칙을 `docs/ci_usage.md` 참조해 설정 권장.

## 🙏 기여

모든 태스크는 Claude Code(오케스트레이터) + Codex(서브에이전트) 협업으로 개발.
편집 책임은 인간 편집자, 생산성 증폭은 Claude.
```

---

## Attach binaries 후보 (선택)

- `output/claude-magazine-2026-05.pdf` (1.6 MB) — 샘플 매거진 PDF
- `output/claude-magazine-2026-04.pdf` (2.4 MB) — 직전 호

첨부 여부는 선택. 발행 중 콘텐츠 샘플을 릴리즈에 첨부하면 독자·기여자가 즉시 품질 확인 가능.
