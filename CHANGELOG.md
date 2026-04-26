# Changelog

## v0.3.0-rc1 — 2026-04-26

5월 31일 정식 발행 1호(Issue 1)의 release candidate. v0.2.1 이후 13 commits — Round 2 디제스트 Gate 1 승인·5월 호 4주 로드맵·외부 큐레이션 파이프라인 5계층 설계·Korea Spotlight·Inside Classmethod 7p Sponsored Content 코너·plan_issue 가이드 + 외부 피드백 시작 준비.

### 콘텐츠·운영 SOP
- **Round 2.B Gate 1 승인** — W3 SNS 디제스트 4 클러스터 approve, 1 hold. 15 source_id를 `data/source_registry.db`에 `rights_status: free / language: ko`로 등록 (commit 9040b4d)
- **Round 2.D W4 디제스트** — SNS 자동화 평일 3일(04-22·23·24) 0건 적재 anomaly 감지. 자매 시스템 정상성 점검 트리거로 첫 활용 (commit 9f88600·055ea80)
- **5월 정식 발행 1호 4주 로드맵** — 1·2주차 콘텐츠 생산, 3·4주차 고도화. 15 본문 + 광고 1 + 구조 8p = **80p 정확 도달 매핑** (`reports/roadmap_2026-05.md` + `reports/plan_issue_2026-05_guide.md`)

### 외부 큐레이션 파이프라인 (신규 SOP)
- **5계층 설계** — L1 수집(RSS·소셜·논문 어댑터 7종) → L2 키워드 필터 → L3 Sonnet/Haiku 요약 → L4 Opus 클러스터링 → L5 Gate 1 채택 (`docs/integrations/external_curation_pipeline.md`)
- **X·Threads 자동 크롤링 기각 명문화** — ToS 위반 위험 + 법적 신뢰성 보호. 편집자 수동 큐레이션 + baoyu-url-to-markdown skill로 대체
- **외부 OSS 5종 채택** (mckinsey-pptx · ai-daily-digest · python-hacker-news · menshun · tech-digest) + 2종 참고 (future-slide-skill · dialectic-digest)

### Korea Spotlight 코너 (자체 콘텐츠 활용)
- **`scripts/curate_classmethodkr_best.py`** — 월별 베스트 기고 큐레이터 (RSS + 휴리스틱 점수, LLM 호출 0회)
- **classmethodkr RSS 피드 추가** (`config/feeds.yml`) + `pipeline/source_ingester.py` `rights_status` 패스스루 1줄 패치
- **4월 시범 큐레이션 1회분** — 14건 중 TOP 5 선정 (`reports/classmethodkr_best_2026-04.md`)
- 매월 Review 카테고리 3p 코너 + 블로그 트래픽 유입 효과

### Inside Classmethod 7p Sponsored Content 코너
- **일본본사 Claude 컨설팅 서비스 + 한국법인 + Claude 오프라인 밋업 1회차(2025-04-23) + Claude 커뮤니티 안내** 통합 7p 구성 (`reports/inside_classmethod_2026-05_draft.md`)
- **`docs/governance.md` §"Sponsored Content" 6 의무 신규 추가** — AD 배지·footer 고지·시각 분리·광고 비율 ≤10%·식별성 footnote·Colophon 명시
- **`scripts/plan_issue.py` `sponsored` 카테고리 신규** (1줄 패치)
- 매호 광고 비율 5월 호 8.75% (≤10% 상한 준수)

### 외부 피드백 시작 준비 (Threads 게시 직전)
- **README.md §"피드백 환영" 신규** — 어떤 피드백을 원하는가 6개 영역 + 경로 4개 (Discussions·Issues·Threads 댓글·이메일)
- **CONTRIBUTING.md 외부 기여자 7 섹션 신규** — 콘텐츠 제안·매거진 정체성·라이선스·Code of Conduct·FAQ
- **GitHub Discussions 활성화 권장** (사용자 액션) + Discussions 카테고리 4종 (Ideas·General·Q&A·Show and tell)

### 운영 도구
- **`scripts/audit_budget.py`** — illustration 월간 예산 감시 CLI (Round 3, commit b906819). `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP` 초과 자동 차단
- **`reports/round2_b_gate1_template_2026-04-W3.md`** + **`reports/round2_d_cowork_w4_prompt.md`** — Round 2 준비 자료

### 인프라·검증
- 97/97 pytest pass (시간 의존 fixture 1건은 별건)
- ruff lint clean / 모든 신규 파일 mojibake clean (UTF-8 검증)
- main 브랜치 v0.2.1 → e66da2a 동기화 완료 (3회 머지)

## v0.2.1 — 2026-04-26

Phase 8 종결 + Cowork × Drive 통합 + 운영 도구 추가. 자세한 내용은 [reports/release_v0.2.1_notes.md](reports/release_v0.2.1_notes.md).

### Phase 8 종결 — 자율 개선 폐쇄 루프
- **TASK_053**: `weekly_improvement` 루프가 cache·citations·illustration·publish 4 운영 신호 소비
- **TASK_054**: 반복 실패 자동 감지 + `weekly_improvement` 우선순위 큐 (3회+ 같은 failure_class) + Slack 알림

### Cowork × Drive 통합
- `docs/integrations/cowork_drive_integration.md` — 시나리오 B (SNS 일일 산출물 → 매거진 큐레이션) 정합 설계
- `docs/integrations/sns_to_magazine_pipeline.md` — SNS → 매거진 운영 SOP

### 운영 도구
- `pipeline/failure_repeat_detector.py` — 14일 윈도우 반복 실패 감지
- `codex_sync.yml` 안정화 — `*_draft.md` 제외 + skip-if-no-change + permissions

### CI · 검증
- CI 7-job 병렬 (lint·smoke·tests·build·env·spec·mojibake) 모두 green
- 53/54 CODEX_TASKS merged

## v0.2.0 — 2026-04-24

매거진 발행 체계의 품질·거버넌스·관측·자동화를 대폭 강화.
v0.1.0 이후 39개 태스크 머지 (TASK_011 v0.1.0 릴리즈 기록, TASK_020 결제 무료발행 정책으로 취소).

### Phase 3 — 품질·법적 리스크·디자인
- TASK_016: 편집 체크리스트 자동 검증 (editorial_lint.py)
- TASK_017: PII 비식별화 파이프라인 (pii_masker.py)
- TASK_018: AI 사용 고지 자동 삽입 (disclosure_injector.py)
- TASK_019: 소스 다양성 규칙 엔진 (source_diversity.py, 4규칙)
- TASK_021: 월간 커버 일러스트 드롭인 시스템 (CoverPage.jsx 확장)
- TASK_022: 매거진 템플릿 확장 (Interview·Review·Feature)
- TASK_023: SNS 카드뉴스 자산 배포 파이프라인
- TASK_024: Ghost Self-Hosted 배포 자동화 (Docker Compose)

### Phase 4 — Miessler AI 원칙
- TASK_025: 기사 이상 상태(Pass/Fail) 스펙 시스템 (article_standards.yml)
- TASK_026: 편집자 판정 누적 시스템 (Expertise Diffusion)
- TASK_027: 자율 개선 루프 (Autonomous Optimization)
- TASK_028: 운영 투명성 대시보드 (Opacity to Transparency)
- TASK_029: 편집자 승인 UI (스캐폴딩 제거)

### Phase 5 — Superpowers + 80페이지 발행 체계
- TASK_030: 매거진 전용 Claude Code Skills (.claude/skills/ 5종)
- TASK_031: Git Worktree 기반 Agent 병렬 위임 표준화
- TASK_032: RSS·Atom 자동 수집 파이프라인 (source_ingester.py)
- TASK_033: Claude Agent SDK 통합 (Max 구독 경유로 API 비용 0)
- TASK_034: 매거진 추가 컴포넌트 (TOC·Editorial·Colophon)
- TASK_035: 80페이지 월간 PDF 컴파일러 (compile_monthly_pdf.py)
- TASK_036: 월간 플랜 관리 CLI (plan_issue.py)
- TASK_037: 월간 발행 원스톱 + 대시보드 진행률 위젯
- TASK_038: typeui.sh 디자인 스킬 선별 도입 (mono·status·type scale)
- TASK_039: Claude Code 2.1.x 신기능 통합 (Opus 1M·/ultrareview·forking)

### Phase 5 확장 — 외부 스킬 + API 효율화
- TASK_040: baoyu-skills High 시너지 4종 도입 (url-to-md·yt·illustrator·infographic)
- TASK_041: 카드뉴스 제작 스킬 + 밀도 게이트 (channel_rewriter 구조화)
- TASK_042: Figma MCP 옵션 조사 + slide JSON 통합 설계안
- TASK_043: 이미지 생성 provider 매트릭스 + illustration_hook ABC 어댑터
- TASK_044: Prompt Caching 도입 (cache 히트율 45.9% 실측, 99% 입력 토큰 감소)
- TASK_045: Citations API 이중 운영 도입 (수동 source_id + Anthropic Citations)
- TASK_046: Figma 실구현 (무료 REST API + paste 패키지 하이브리드)
- TASK_047: 이미지 backend 실구현 (무료 전용: Pollinations + HuggingFace,
  fallback chain + 예외 타입 정규화)

### Phase 6 — 운영 관측 + 엔지니어링 성숙도
- TASK_048: 운영 관측 위젯 (cache·citations·illustration 대시보드 확장)
- TASK_049: editorial_lint pytest 스위트 (15 체크, 커버리지 editorial_lint
  85% / citations_store 90%)

### Phase 7 — 발행 신뢰성·배포 자동화
- TASK_050: publish_monthly UX (--status·--reset-stage·--from-stage + 텔레메트리)
- TASK_051: 발행 실패 복구 플레이북 (7 stage × 14 failure class, 자동 가이드 생성)
- TASK_052: GitHub Actions CI 확장 (7 job 병렬:
  lint·smoke·tests·build·env·spec·mojibake)

### 기술 스택 변경·추가
- LLM 효율화: Prompt Caching (TASK_044), Citations API 병행 (TASK_045)
- 모델: Opus 4.7 1M context + /ultrareview + Subagent Forking (TASK_039)
- 이미지: IllustrationProvider ABC + Pollinations·HuggingFace·OpenAI fallback
  chain (TASK_047)
- 외부 스킬: jimliu/baoyu-skills wrapper 4종 + card-news-builder 전용 skill
- 테스트: pytest + pytest-cov (TASK_049)
- CI: GitHub Actions 7 job 병렬 (TASK_052)

### 운영 정책
- 무료 발행 원칙 유지 (결제 기능 없음, PortOne 도입 취소)
- Agent SDK Max 구독 경유로 LLM API 비용 0 (TASK_033)
- 이미지 생성 기본 경로 Pollinations.ai (무료 + 인증 불필요, TASK_047)
- 월간 illustration 비용 상한 env로 기술적 차단 (기본값 $0)

### 지표 (2026-04-24 기준)
- 머지된 태스크: 50개 (TASK_001~052, 020 cancelled)
- pytest: 38/38 통과
- 커버리지: editorial_lint 85%, citations_store 90%
- CI job: 7개 병렬
- cache 히트율 실측: 45.9%

## v0.1.0 — 2026-04-21

### Phase 1 — 콘텐츠 파이프라인
- TASK_001: 프로젝트 초기 설정 (.env, data/, drafts/, logs/)
- TASK_002: Ghost CMS 연동 (JWT 인증, create_post, send_newsletter)
- TASK_003: Claude API 기사 브리프 파이프라인 (Sonnet 4.6)
- TASK_004: 출처 레지스트리 시스템 (SQLite)
- TASK_005: 팩트체크 에이전트 (Opus 4.7)
- TASK_006: 주간 브리프 발행 스크립트
- TASK_007: n8n 워크플로우 자동화 (스케줄러·발행·SNS 3종)
- TASK_008: Langfuse 관측 연동
- TASK_009: React 매거진 레이아웃 (Cover·Article·Insight)
- TASK_010: Puppeteer 월간 PDF 생성

### Phase 2 — 운영 준비
- TASK_012: 운영환경 체크 스크립트 (check_env.py, 8개 항목)
- TASK_013: 주간 브리프 E2E 스모크 테스트 (test_e2e.py)
- TASK_014: n8n 워크플로우 import 자동화 (n8n_import.py)
- TASK_015: Ghost Webhook 자동 등록 (ghost_webhook_setup.py)

### 기술 스택
- LLM: Claude Sonnet 4.6 / Opus 4.7 / Haiku 4.5
- CMS: Ghost Admin API v4
- DB: SQLite
- 워크플로우: n8n
- 관측: Langfuse
- 프론트: Vite + React + Tailwind + Recharts
- PDF: Puppeteer (Node.js)
