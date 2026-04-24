# Development Backlog

Open ideas that are not active `TASK_*.md` specs yet belong here. Once promoted to a formal task, remove them from this file.

---

## Cost Tracking 중앙화

**출처**: [BerriAI/litellm](https://github.com/BerriAI/litellm) 시너지 분석 (2026-04-24)
**규모**: 중간 (~90분)

현재 비용 집계가 분산됨:
- LLM: TASK_044 cache 로그 + TASK_048 metrics_collector
- Illustration: TASK_047 `cost_estimate` + TASK_048 illustration budget
- Citations: TASK_045 token cost 추정

### 아이디어
`pipeline/cost_tracker.py` 공통 모듈 신설:
```python
def record_cost(source: str, usd: float, metadata: dict) -> None: ...
def month_total(month: str | None = None) -> dict: ...
```
- 모든 파이프라인이 단일 진입점으로 비용 보고
- TASK_048 대시보드가 단순 소비 (집계 로직 pipeline 쪽으로 이동)

### 언제 착수
- TASK_048 대시보드가 실제 운영 데이터 2~4주 축적 후
- 분산 집계 로직에 버그나 불일치가 발생하면 즉시

### 스택 제약
- 새 DB 도입 금지 — JSON 파일(`logs/cost_log.jsonl`) 또는 기존 SQLite(`data/source_registry.db`) 재사용

---

## CI 예산 감시 Job

**출처**: [BerriAI/litellm](https://github.com/BerriAI/litellm) 시너지 분석 연장
**규모**: 작음 (~30분), TASK_052 머지 후 진행

TASK_052 CI에 6 job 분할됨. 후속 태스크 후보:
- `budget-audit` job 추가 — 월간 누적 비용이 임계 초과 시 CI 실패
- 임계: `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP` + LLM 자체 상한 합계
- 초과 시 Slack 알림 (TASK_028 알림 채널 재사용)

### 언제 착수
- TASK_052 머지 완료
- cost_tracker 중앙화(위 항목)가 있으면 집계가 깔끔

---

## 추가 pytest 커버리지 확장

**출처**: TASK_049 merge 후 식별
**규모**: 중간 (~60분 × 모듈 단위)

TASK_049는 `editorial_lint` + `citations_store` 커버리지 80%/90%. 다음 대상:
- `pipeline/fact_checker.py` — Citations API 이중 운영 경로 mock
- `pipeline/claude_provider.py` — cache_system 옵션·provider 분기
- `pipeline/illustration_hook.py` — fallback chain (부분적으로 TASK_047이 추가)
- `scripts/publish_monthly.py` — stage 함수별 (TASK_050이 일부 추가)

### 언제 착수
- Phase 7 이후 정기 품질 유지보수
- 특정 pipeline에 대형 수정이 예정될 때 선행 투자

---

## Anthropic Courses 한국어 해설 연재 아이디어

**출처**: [anthropics/courses](https://github.com/anthropics/courses) 시너지 분석 (2026-04-24)
**규모**: 편집 기획 (개발 태스크 아님)

### 매거진 콘텐츠 소재 풀
Anthropic 공식 커리큘럼 5 코스 + Jupyter 노트북 → 한국어권 독자 공백 영역.
매거진 연재 기사로 재가공 가능.

| 코스 | 매거진 활용 각도 |
|---|---|
| anthropic_api_fundamentals | "Claude API 시작하기 — 한국어 개발자용 실전 가이드" |
| prompt_engineering_interactive_tutorial | 주간 브리프 시리즈로 분할 (한 회차 = 한 기법) |
| real_world_prompting | Cover Story — "실전 프롬프트 디자인 패턴" |
| prompt_evaluations | 심층 기사 — 매거진 TASK_025 Pass/Fail 체계와 대조 |
| tool_use | Feature — "Tool use로 만드는 한국어 자동화 에이전트" |

### 편집 원칙 (중요)
- 원문 충실도 규칙(TASK_025) 엄수 — Jupyter 노트북 코드를 **번역이 아닌 해설**로
- source_id 연결 + Citations API(TASK_045) 자동 생성으로 출처 투명성 확보
- AI 사용 고지(TASK_018) 삽입

### 개발 태스크 아님
매거진 **기술 스택에 추가 개발 불필요**. `plan_issue.py`(TASK_036) 월간 플랜에
편집자가 수동으로 기획 시 본 항목을 참조.

### 언제 착수
- 월간 플랜 수립 시 매월 1회차씩 배정 검토
- TASK_046 Figma 파이프라인 활용하면 커리큘럼 해설 카드뉴스도 생산 가능

---

## Archived Notes

### publish_monthly UX

This item was promoted to [TASK_050](../tasks/TASK_050.md) on 2026-04-24 and is no longer tracked in backlog form.
