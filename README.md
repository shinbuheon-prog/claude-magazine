# Claude Magazine

[![Release](https://img.shields.io/github/v/release/shinbuheon-prog/claude-magazine?include_prereleases&label=release)](https://github.com/shinbuheon-prog/claude-magazine/releases)
[![License](https://img.shields.io/badge/license-Internal-blue)](#license)
[![pytest](https://img.shields.io/badge/pytest-96%2F97-green)](#testing)
[![Issue 1](https://img.shields.io/badge/Issue%201-2026--05--31-orange)](reports/roadmap_2026-05.md)
[![Free Publishing](https://img.shields.io/badge/publishing-free-green)](#운영-정책)
[![Sponsored ≤ 10%](https://img.shields.io/badge/sponsored-%E2%89%A410%25-blue)](docs/governance.md)

> 한국어권 Claude 실무자를 위한 무료 발행 매거진. **인간 편집 책임 위에 Claude가 생산성을 증폭하는 운영체계**.

---

## 정체성

매거진은 단순한 콘텐츠 모음이 아니라 **AI·인간 협업 발행 시스템**입니다.

- 편집자(인간)가 모든 발행 결정·정정 책임을 갖는다
- Claude 계열 모델이 브리프·초안·팩트체크·운영 신호 분석을 보조한다
- Codex(서브에이전트)는 코드 구현 단위로 위임된다
- Cowork 자동화 도구가 외부 데이터 소스와 매거진 사이의 매개 역할을 한다

```
Cowork ─→ Drive 데이터 분석·디제스트 자동 생성
   ↓
Claude Code ─→ 매거진 콘텐츠 파이프라인·코드 리뷰
   ↓
Codex ─→ TASK_*.md 단위 구현 위임
   ↓
편집자 (인간) ─→ Gate 1·Gate 2 승인 + 모든 발행 결정
```

---

## 운영 정책

### 무료 발행 원칙
매거진은 **전면 무료**로 발행됩니다. 결제·유료 구독 시스템 도입 금지(TASK_020 cancelled).

### LLM 비용 0
Claude Agent SDK + Max 구독 경유로 **API 비용 $0**(TASK_033). 외부 모델 호출이 필요한 경우 무료 provider 우선(Pollinations·HuggingFace, TASK_047).

### 이미지 비용 가드
`CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=0.0` 기본값으로 유료 이미지 provider 자동 차단. 활성화 시 `scripts/audit_budget.py --strict`로 cap 초과를 기술적으로 강제.

### 한국어 편집 표준
- **em-dash(—)** 사용 (하이픈 - 으로 무단 변경 금지)
- 본문: **Noto Serif KR** (세리프)
- SNS 카드: **Pretendard / Noto Sans KR** (산세리프)
- 모든 주장에 `source_id` 연결 + Citations API 자동 검증

---

## 기술 스택

| 영역 | 선택 |
|---|---|
| LLM | Claude Sonnet 4.6 / Opus 4.7 / Haiku 4.5 (모델 배치 규칙: CLAUDE.md) |
| CMS | Ghost Admin API v4 |
| 출처 DB | SQLite (`data/source_registry.db`) |
| 워크플로우 | n8n |
| 관측 | Langfuse |
| 프론트 | Vite + React + Tailwind + Recharts |
| PDF | Puppeteer (Node.js) |
| 테스트 | pytest 8+ + pytest-cov |
| CI | GitHub Actions (7 job 병렬) |

---

## 핵심 기능 (v0.2.1)

### 콘텐츠 파이프라인
- **brief_generator**: 주제 → 기사 brief (Sonnet 4.6)
- **draft_writer**: brief → 초안 (Sonnet 4.6)
- **fact_checker**: 초안 + Citations API → 사실 확인 (Opus 4.7)
- **channel_rewriter**: SNS 4 채널 재가공 (Haiku 4.5)
- **publish_monthly**: 80페이지 월간 PDF 원스톱 발행

### 품질 게이트
- **editorial_lint**: 11 article checks + 4 card-news checks (TASK_016·045)
- **standards_checker**: TASK_025 Pass/Fail 카테고리별
- **source_diversity**: 4 규칙 (언어·관점·발행처·시효성)
- **publish-gate skill**: 통합 발행 게이트

### 운영 관측
- **dashboard**: 매거진 운영 투명성 대시보드 (TASK_028)
- **운영 신호 위젯**: cache·citations·illustration provider 추세 (TASK_048)
- **failure_repeat_detector**: 3회+ 반복 실패 자동 감지 + Slack 알림 (TASK_054)
- **audit_budget**: 월간 illustration 예산 감시 CLI

### 자율 개선
- **weekly_improvement**: 운영 신호 4종 + 반복 실패 큐 → Sonnet 분석 → SOP 제안서
- **편집자 승인 필수** — 자동 코드·SOP 변경 금지

### 외부 통합
- **Figma**: 무료 REST API + paste 패키지 하이브리드 (TASK_046)
- **Cowork × Google Drive**: SNS 운영 폴더 → 매거진 콘텐츠 소스 (시나리오 B 연계)
- **baoyu-skills**: 4종 wrapper (url-to-md·yt-transcript·illustrator·infographic)

---

## 프로젝트 구조

```
claude-magazine/
├── CLAUDE.md              # 에이전트 OS — 모델 배치·코딩 규칙
├── AGENTS.md              # Codex 위임 패턴 + Worktree
├── CHANGELOG.md           # 버전별 변경 이력
├── CODEX_TASKS            # 태스크 보드 (53 merged)
├── codex_workflow.py      # 보드 관리 CLI
├── README.md              # 본 파일
│
├── pipeline/              # Claude API 파이프라인
│   ├── brief_generator.py
│   ├── draft_writer.py
│   ├── fact_checker.py
│   ├── channel_rewriter.py
│   ├── editorial_lint.py
│   ├── citations_store.py
│   ├── failure_collector.py
│   ├── failure_playbook.py
│   ├── failure_repeat_detector.py
│   ├── illustration_hook.py
│   ├── illustration_providers/
│   ├── source_ingester.py
│   ├── source_registry.py
│   └── ...
│
├── scripts/               # 운영 진입점·CLI
│   ├── run_weekly_brief.py
│   ├── publish_monthly.py
│   ├── compile_monthly_pdf.py
│   ├── plan_issue.py
│   ├── audit_budget.py    # 월간 예산 감시
│   ├── weekly_improvement.py
│   └── ...
│
├── web/                   # 매거진 프론트엔드 (Vite + React)
│   └── src/
│       ├── components/    # CoverPage·ArticlePage·InsightPage 등 9 컴포넌트
│       └── pages/         # DashboardPage·admin/...
│
├── tasks/                 # Codex 위임 명세서 (TASK_001~054)
├── docs/                  # 운영 문서
│   ├── automation_design.md
│   ├── editorial_checklist.md
│   ├── governance.md
│   ├── source_policy.md
│   ├── monthly_publish_runbook.md
│   ├── ci_usage.md
│   ├── failure_playbook_catalog.md
│   ├── backlog.md
│   └── integrations/
│       ├── cowork_drive_integration.md
│       ├── cowork_project_context.md
│       └── sns_to_magazine_pipeline.md
│
├── spec/                  # 기사 이상 상태 스펙
│   ├── article_standards.yml
│   ├── card_news_standards.yml
│   └── failure_playbook.yml
│
├── tests/                 # pytest 스위트 (97 tests)
├── reports/               # 자율 개선 보고서·디제스트
├── config/                # 운영 설정 (feeds.yml 등)
├── .claude/skills/        # Claude Code Skills 11종
└── .github/workflows/     # CI (ci.yml + codex_sync.yml)
```

---

## 시작 가이드

### 환경 설정
```bash
# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 테스트 추가

# .env 파일 생성 (예시 복사)
cp .env.example .env
# 필요한 키 입력: ANTHROPIC_API_KEY (Max 구독 경유 시 불필요), GHOST_*, NOTIFY_SLACK_WEBHOOK 등
```

### 운영환경 검증
```bash
# 8개 항목 점검 (.env·DB·API 키 등)
python scripts/check_env.py --strict
```

### 주간 브리프 발행
```bash
# 드라이런 (API 호출 없음)
python scripts/run_weekly_brief.py --topic "Claude Code 멀티에이전트" --dry-run

# 실제 발행
python scripts/run_weekly_brief.py --topic "Claude Code 멀티에이전트" --publish
```

### 월간 매거진 발행
```bash
# 1. 월간 플랜 초기화
python scripts/plan_issue.py init --month 2026-05 --theme "AI 에이전트 운영"

# 2. publish_monthly 단계별 진행
python scripts/publish_monthly.py --month 2026-05 --dry-run     # 시뮬레이션
python scripts/publish_monthly.py --month 2026-05 --status      # 진행 상태만
python scripts/publish_monthly.py --month 2026-05 --publish --confirm  # 실제 발행

# 3. 단계별 재실행
python scripts/publish_monthly.py --month 2026-05 --reset-stage pdf_compile --yes
python scripts/publish_monthly.py --month 2026-05 --from-stage pdf_compile
```

### 운영 도구
```bash
# 월간 illustration 예산 감시
python scripts/audit_budget.py --strict --notify

# 반복 실패 감지
python pipeline/failure_repeat_detector.py --window 14 --threshold 3

# 주간 개선 루프
python scripts/weekly_improvement.py --since-days 7
```

---

## 테스트

```bash
# 전체 실행
pytest -v

# 커버리지 측정
pytest --cov=pipeline.editorial_lint --cov=pipeline.citations_store --cov-report=term

# 특정 모듈만
pytest tests/test_failure_collector.py -v
```

**현재 상태** (v0.3.0-rc1, 2026-04-26):
- 97 tests / **96 passed** (1 fail: `test_collect_operational_signals` — 시간 의존 fixture 별건, [issue 후속 fix 예정](https://github.com/shinbuheon-prog/claude-magazine/issues))
- editorial_lint 85% / citations_store 90% 커버리지
- ruff lint clean
- CI 7 job 병렬 (lint·smoke·tests·build·env·spec·mojibake) 모두 green
- 모든 신규 파일 mojibake clean (UTF-8 검증)

---

## 협업 모델

매거진은 4자 협업으로 개발됩니다.

| 역할 | 책임 |
|---|---|
| **편집자 (인간)** | 발행 결정·정정 책임·Gate 1/Gate 2 승인 |
| **Claude Code** | 설계·태스크 정의·코드 리뷰·머지 검증 |
| **Codex** | TASK_*.md 단위 구현 위임 |
| **Cowork** | Drive 데이터 분석·주간 디제스트 자동 생성 |

자세한 위임 패턴은 [AGENTS.md](AGENTS.md)와 [docs/integrations/cowork_drive_integration.md](docs/integrations/cowork_drive_integration.md) 참조.

---

## 운영 SOP

| 문서 | 용도 |
|---|---|
| [docs/editorial_checklist.md](docs/editorial_checklist.md) | 발행 전 10개 필수 체크 |
| [docs/governance.md](docs/governance.md) | AI 사용 고지·개인정보 처리 |
| [docs/source_policy.md](docs/source_policy.md) | rights_status·인용 한도 |
| [docs/monthly_publish_runbook.md](docs/monthly_publish_runbook.md) | 월간 발행 캘린더 + 트러블슈팅 |
| [docs/integrations/sns_to_magazine_pipeline.md](docs/integrations/sns_to_magazine_pipeline.md) | SNS 일일 산출물 → 매거진 큐레이션 |
| [docs/failure_playbook_catalog.md](docs/failure_playbook_catalog.md) | 7 stage × 14 failure class 복구 가이드 |
| [docs/ci_usage.md](docs/ci_usage.md) | CI job 구성·main 브랜치 보호 규칙 |

---

## Phase 진행 현황

| Phase | 범위 | 상태 |
|---|---|---|
| 1 | 콘텐츠 파이프라인 (TASK_001~010) | ✅ v0.1.0 |
| 2 | 운영 준비 (TASK_012~015) | ✅ v0.1.0 |
| 3 | 품질·법·디자인 (TASK_016~024) | ✅ v0.2.0 |
| 4 | Miessler AI 원칙 (TASK_025~029) | ✅ v0.2.0 |
| 5 | Superpowers + 80p 발행 + 외부 스킬 (TASK_030~047) | ✅ v0.2.0 |
| 6 | 운영 관측 + 엔지니어링 성숙 (TASK_048~049) | ✅ v0.2.0 |
| 7 | 발행 신뢰성·배포 자동화 (TASK_050~052) | ✅ v0.2.0 |
| 8 | 자율성 강화 (TASK_053~054) | ✅ v0.2.1 |

전체 변경 이력은 [CHANGELOG.md](CHANGELOG.md) 참조.

---

## 피드백 환영 (2026-05 정식 발행 1호 준비 중)

매거진은 **2026-05-31 정식 발행 1호(Issue 1)**를 앞두고 외부 피드백을 받고 있습니다. 한국어권 Claude 사용자 관점의 의견을 환영합니다.

### 어떤 피드백을 원하는가
- 어떤 Claude 주제를 매거진에서 보고 싶은가 (콘텐츠 제안)
- 한국어권 Claude 사용자 관점에서 부족한 콘텐츠 영역
- 매거진 운영 모델(무료 발행 + 인간 편집 + AI 보조 + 자체 사례 + 외부 큐레이션)에 대한 의견
- AWS Bedrock·MCP·Cowork·Claude Code 운영 경험·트러블슈팅 사례 (매거진 본문 source 후보)
- 디자인·레이아웃·페이지 구성 (80p PDF · Vite+React+Puppeteer 출력)
- 발행 자동화 운영 정책 (무료 LLM 운영·Sponsored Content 표기 6 의무·소셜 채널 자동 크롤링 기각 등)

### 피드백 경로
| 경로 | 대상 | 진입 장벽 |
|---|---|---|
| **GitHub Discussions** | 콘텐츠 제안·운영 모델 의견·일반 토론 | GitHub 계정 |
| **GitHub Issues** | 버그 리포트·기능 제안·구체 사양 변경 | GitHub 계정 |
| **Threads 댓글** (각 게시 시점) | 비개발자·간단한 의견 | Threads 계정 |
| **이메일** (info@classmethod.kr) | 협업·콘텐츠 제공·직접 연락 | 없음 (governance §"개인정보 처리 원칙" 30일 내 삭제) |

상세 가이드: [CONTRIBUTING.md](CONTRIBUTING.md)

## 기여

매거진은 현재 1인 편집자 + AI 보조 모델로 운영됩니다. 외부 기여는 다음 경로:

- **콘텐츠 제안·운영 모델 토론**: GitHub Discussions (가장 환영)
- **버그 리포트·기능 제안**: GitHub Issues
- **코드 기여**: PR 환영 — 기여 전 [CONTRIBUTING.md](CONTRIBUTING.md) 및 [CLAUDE.md](CLAUDE.md) 코딩 규칙 일독
- **Sponsored Content 협업·문의**: 발행사 클래스메소드(코리아 법인) info@classmethod.kr (governance.md §"Sponsored Content" 6 의무 준수)

---

## License

매거진 소스는 내부 운영 코드입니다. 발행된 콘텐츠는 매거진 라이선스 정책에 따름.
구체 조건은 향후 공식 라이선스 문서 추가 시 명시 예정.

---

## 관련 링크

- **Releases**: https://github.com/shinbuheon-prog/claude-magazine/releases
- **CHANGELOG**: [CHANGELOG.md](CHANGELOG.md)
- **에이전트 OS**: [CLAUDE.md](CLAUDE.md) (모델 배치·코딩 규칙)
- **위임 패턴**: [AGENTS.md](AGENTS.md)
- **태스크 보드**: [CODEX_TASKS](CODEX_TASKS)
- **백로그**: [docs/backlog.md](docs/backlog.md)

---

> "AI는 편집자를 대체하지 않습니다. 편집자가 더 많은 것을 더 잘하게 합니다."
