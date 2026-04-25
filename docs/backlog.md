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

## CI 예산 감시 — `scripts/audit_budget.py` (부분 완료, 2026-04-25)

**출처**: [BerriAI/litellm](https://github.com/BerriAI/litellm) 시너지 분석 연장
**상태**: ⚠️ **CLI 도구 완료, CI 통합은 후속**

### 완료 (2026-04-25, Round 3 직접 구현)
- `scripts/audit_budget.py` CLI 신설
  - `data/illustration_cost_<YYYY-MM>.json` 읽어 cap 대비 utilization 산출
  - `CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP` env 또는 `--cap` override
  - 모드: 텍스트·JSON·`--strict`(초과 시 exit 1)·`--notify`(80% 이상 Slack)
  - `--month` 지정 가능 (기본 이번 달 UTC)
- `tests/test_audit_budget.py` — 16 tests, 충분한 커버리지

### 후속 (남은 부분)
- LLM cost(`logs/factcheck_*.json` cache cost) 추가 추적 — 현재는 illustration만
- CI ci.yml에 `budget-audit` job 추가 — 단, `data/`는 gitignore라 CI 실데이터 부재.
  대안: artifact upload from publish_monthly 또는 Slack 알림만 운영 인프라로
- cost_tracker 중앙화(아래 항목)와 통합 — illustration·LLM·citations 단일 진입점

### 언제 추가 작업 착수
- 운영 데이터 2~4주 축적 후 LLM cost 통합
- publish_monthly 실전 가동 시 artifact 흐름 설계

### 운영 사용 예시
```bash
# 이번 달 현황 (텍스트)
python scripts/audit_budget.py

# JSON 출력 (자동화 통합용)
python scripts/audit_budget.py --json

# CI/cron 모드 — cap 초과 시 exit 1 + Slack 알림
python scripts/audit_budget.py --strict --notify

# 특정 달 임시 점검
python scripts/audit_budget.py --month 2026-05 --cap 5.0
```

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

## design-extractor skill (참조 이미지 → DESIGN.md 자동 추출)

**출처**: [jyoung105/future-slide-skill](https://github.com/jyoung105/future-slide-skill) 시너지 분석 (2026-04-25)
**규모**: 중간 (~90~120분)

future-slide-skill의 `gpt-slide-design`은 참조 이미지에서 디자인 시스템(폰트·색·zoning·레이아웃 규칙)을 `DESIGN.md`로 추출하는 별도 skill로 분리. 매거진의 TASK_038(typeui 분석)이 1회성 작업이었던 것을 **재사용 가능한 skill**로 승격할 영감.

### 아이디어
`.claude/skills/design-extractor/SKILL.md` 신규:
- 입력: 참조 이미지(스크린샷·PDF) + 의도(예: "월간 커버 톤 변경")
- 출력: `docs/design_systems/<name>.md` — 폰트·컬러·zoning·여백·정렬 규칙 추출
- 후속 적용: `web/src/theme.js` 토큰 패치 제안 (실제 적용은 편집자 승인 후)

### 언제 착수
- 편집자가 디자인 다양화·교체 요구 명시 시
- 월간 커버 디자이너 결과물에서 자동 추출 수요 발생 시
- 또는 새 SNS 카드뉴스 톤 변경 필요 시

### 스택 제약
- Claude Code 표준 skill 패턴 준수 (frontmatter + Procedure + Verify)
- TASK_038에서 도입한 `theme.js` 토큰 구조 호환
- 외부 이미지 분석 모델 사용 시 무료 발행 원칙 정합성 확인

---

## InsightPage 차트 카탈로그 확장

**출처**: [seulee26/mckinsey-pptx](https://github.com/seulee26/mckinsey-pptx) 시너지 분석 (2026-04-25)
**규모**: 중간 (~60~90분)

mckinsey-pptx는 40 슬라이드 템플릿 중 차트(heatmap·2×2 matrix·bubble·stacked column·forecast)를 풍부하게 보유. 매거진 [InsightPage.jsx](../web/src/components/InsightPage.jsx)는 현재 layout 3종(comparison·timeline·process-flow)만 지원.

### 아이디어
- InsightPage에 추가 layout 4종 도입: `heatmap`·`matrix-2x2`·`bubble`·`forecast`
- 데이터 시각화 비중 큰 기사(특집·심층 분석)에서 활용
- `plan_issue.py`(TASK_036)가 기사 카테고리에 따라 적합 차트 자동 추천 (선택)

### 언제 착수
- 기사 중 데이터 시각화 비중 증가 시 (편집자 요구)
- `prompt_evaluations` 코스 해설 기사처럼 비교·분류 데이터가 핵심인 콘텐츠 작업 시
- 사용 빈도가 현재 3 layout으로 부족하다고 판단되는 시점

### 스택 제약
- Recharts 기반 유지 (`react`·`recharts` 이미 설치)
- mckinsey-pptx PPTX 직접 통합은 **비권장** (포맷·톤 미스매치, 본 항목은 차트 종류만 차용)
- McKinsey 컨설팅 톤 강제 금지 — 매거진 잡지 톤(Noto Serif KR + 따뜻한 navy) 유지

---

## editor_corrections 기반 editorial_lint heuristic 자동 학습 (Phase 8 잔여)

**출처**: TASK_054 후속 후보 (편집자가 Phase 8 closure 시 백로그로 이동, 2026-04-25)
**규모**: 큼 (~120~180분)

TASK_026 편집자 판정 누적(`data/editor_corrections.db`)을 입력으로 editorial_lint heuristic 자동 보강 제안서 생성.

### 아이디어
`pipeline/lint_heuristic_learner.py` 신규:
- editor_corrections.db 스캔 → "편집자가 lint False Positive로 판정한 케이스" 추출
- Sonnet 호출로 heuristic 보강 제안서 생성
- `reports/lint_heuristic_proposal_*.md` 형태로 저장 — **자동 적용 금지**, 편집자 검토 필수

### 왜 백로그에 머무는가
- editor_corrections.db에 충분한 데이터 축적이 선행되어야 함 (수개월 단위)
- TASK_027 sop_updater와 역할 분리·중복 검토 필요
- 자동 학습 잘못되면 체크 기준 왜곡 → 안전장치 설계 비중이 높음

### 언제 착수
- editor_corrections에 100건+ 데이터 축적 후
- TASK_055로 승격 시 안전장치(승인 워크플로우) 명세 우선

---

## weekly_improvement --auto-trigger 옵트인 모드 (Phase 8 잔여)

**출처**: TASK_054 후속 후보 (Phase 8 closure 시 백로그로 이동, 2026-04-25)
**규모**: 중간 (~60~90분)

TASK_054의 `--trigger-improvement`는 수동 confirmation prompt. 신뢰가 쌓이면 자동 실행도 옵션으로 제공.

### 아이디어
- env: `CLAUDE_MAGAZINE_AUTO_TRIGGER_IMPROVEMENT=true` (기본 false)
- 활성 시 큐 마커 작성 즉시 weekly_improvement 자동 호출
- Debounce: 같은 class에 24h 내 1회만 자동 실행
- 자동 실행 로그 + Slack 알림 (TASK_054에서 추가된 notify_slack 재사용)

### 왜 백로그에 머무는가
- false positive 1건당 Opus 호출 비용 발생
- 매거진 운영 데이터 축적·실전 발행 경험 후 신뢰도 판단 필요
- TASK_054의 수동 트리거가 충분히 작동하는지 먼저 검증

### 언제 착수
- TASK_054 머지 후 4주+ 운영 데이터로 false positive 비율 측정
- 비율이 낮고 수동 트리거가 번거로우면 승격

---

## SNS 디제스트 갭 분석 — 2026-05 brief 큐 후보 5건

**출처**: [reports/monthly_digest_2026-04-W3.md](../reports/monthly_digest_2026-04-W3.md) §3 갭 분석 (Cowork 시범 큐레이션, 2026-04-25)
**규모**: 편집 기획 (개발 태스크 아님, 각 brief 자체는 brief_generator 표준 흐름)

2026-04 W3 SNS 산출물이 **AWS Bedrock × Claude Code 운영 트러블슈팅**에 강하게 편중. 매거진 폭을 위해 SNS에 의존하지 않는 신규 brief 5건을 후보로 등록 (`gap_analysis` 라벨).

### 신규 brief 후보

| 갭 영역 | 신규 brief 제안 | 비고 |
|---|---|---|
| 비개발자 페르소나 | "Cowork로 매거진 SOP를 운영한 한 달" 본인 사례 | 매거진 자체 운영 회고 — Phase 8 closure 후 자연스러움 |
| 거버넌스·법무 | "AI 기본법 시행 100일, 매체사가 점검할 5가지" | `docs/governance.md` 실전판 |
| 한국어 편집 품질 | "한국어 매체에서 Claude를 쓰는 편집 가이드 v1" | 편집 표준 문서화 — em-dash·Noto Serif KR 등 |
| 외부 생태계 비교 | "Claude Code vs. Cursor vs. Replit Agent — 운영자 시점 비교" | 매거진 정체성에 정합 |
| 도입 ROI·정량 사례 | "Claude Max 구독 1팀 6개월 — API 비용 0원 운영기" | 무료 발행 정책과 직접 정합 (TASK_033) |

### 언제 착수
- 2026-05 월간 plan_issue 작성 시 (TASK_036) 편집자가 위 5건 중 N건 선택해 정식 plan 항목화
- 또는 brief_generator 큐의 `gap_analysis` 라벨로 별도 트랙 운영

### 처리 옵션
- **옵션 a**: 본 backlog에 보존, 5월 plan_issue 작성 시 편집자 선택 (현 상태)
- **옵션 b**: `drafts/brief_queue/gap_analysis_2026-05.yml` 신규 — brief_generator가 직접 읽도록
- **옵션 c**: 5건 중 1~2건만 즉시 brief 작성 → 매거진 자체 운영 회고("Cowork SOP 한 달") 우선 진행

### 메모
- SNS 산출물 클러스터링 결과(Cluster A·B·C·D·E)는 Gate 1 승인 후 source_registry 등록 → 별도 brief로 진행 (본 갭 분석과 독립)

---

## Archived Notes

### publish_monthly UX

This item was promoted to [TASK_050](../tasks/TASK_050.md) on 2026-04-24 and is no longer tracked in backlog form.
