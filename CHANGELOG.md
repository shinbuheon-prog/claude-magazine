# Changelog

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
