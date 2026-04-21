# Changelog

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
