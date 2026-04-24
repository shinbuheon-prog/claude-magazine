# TASK_047 Draft (illustration backend 실구현 후속)

## Meta
- status: draft
- prerequisites: TASK_043
- type: implementation
- note: 기존 "TASK_045 Draft"이 TASK_045(Citations API)와 ID 충돌하여 TASK_047로 재부여

## Goal
Activate a real illustration backend behind `pipeline/illustration_hook.py`.
TASK_043에서 OpenAI provider 스켈레톤이 `pipeline/illustration_providers/openai.py`에 선행 구축되었으므로,
본 태스크는 ① 운영 가드레일(월 한도·실수 전환 방지) ② 1차 권장안 선정(로컬 FLUX 또는 OpenAI 저 quality) ③ 비용 모니터링 대시보드 연동.

## Proposed Scope
- Choose one backend only: local FLUX first, OpenAI second
- Respect `CLAUDE_MAGAZINE_ILLUSTRATION_PROVIDER` (TASK_043에서 도입, 기본값 `placeholder`)
- Preserve placeholder fallback
- Log `provider`, `model`, `request_id`, `cost_estimate`, and `license`
- 월 비용 상한 env (예: `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP=5`) 및 초과 시 자동 placeholder fallback

## Non Goals
- No multi-provider orchestration
- No unofficial browser automation wrappers
- No removal of placeholder fallback
