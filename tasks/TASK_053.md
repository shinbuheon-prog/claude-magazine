# TASK_053 — weekly_improvement 루프에 cache·citations·illustration·publish 신호 소비 추가

## 메타
- **status**: todo
- **prerequisites**: TASK_027 (자율 개선 루프 전체), TASK_044 (cache), TASK_045 (citations), TASK_047 (illustration providers), TASK_048 (metrics_collector), TASK_050 (publish_monthly telemetry)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요 (단일 수정 흐름)
- **Phase**: 8 (자율성 강화 — 관측 → 자율 제안 폐쇄 루프)

---

## 목적
TASK_027 자율 개선 루프(failure_collector + sop_updater + weekly_improvement)는 편집·팩트체크·편집자 판정 등 **콘텐츠 품질 신호**만 소비. v0.2.0에서 신설된 **운영·비용 신호는 대시보드에만 노출**되고 자율 개선 루프가 사용하지 않음.

### 해결하는 운영 질문
- cache 히트율이 주차별로 떨어지고 있다면 → 어떤 파이프라인·프롬프트 변경이 원인인가?
- citations cross-check의 warn-mismatch가 누적되면 → 어떤 출처 포맷·기사 유형에서 불일치가 많은가?
- illustration provider fallback이 잦아지면 → 기본 provider 전환 시점인가?
- publish_monthly 특정 stage의 duration_sec이 길어지면 → 병목 자동 감지

### 폐쇄 루프 완성
```
관측 (TASK_028 대시보드 + TASK_048 신규 위젯)
    ↓
실패·이상 수집 (TASK_027 failure_collector + 본 태스크로 신호 5종 확장)
    ↓
Opus 분석 + 제안서 (TASK_027 sop_updater)
    ↓
주간 개선 리포트 (reports/improvement_YYYY-MM-DD.md)
    ↓
편집자 승인 → 코드 반영 (수동)
    ↓
관측에 반영 → 루프 반복
```

---

## 구현 명세

### Phase 1: failure_collector 수집 함수 4종 추가 (30분)

[pipeline/failure_collector.py](../pipeline/failure_collector.py)의 `collect_failures()` 반환 dict에 4개 신규 섹션 추가.

#### 1.1 `collect_cache_signals(since_days)` — cache 효과 추세
- 소스: `logs/factcheck_*.json`·`logs/brief_*.json`·`logs/draft_*.json` 중 `cache_creation_input_tokens`·`cache_read_input_tokens` 필드
- 반환:
  ```python
  {
    "pipelines": {
      "fact_checker": {
        "runs": int,
        "cache_enabled_runs": int,
        "hit_rate_trend": [  # 일별
          {"date": "2026-04-18", "hit_rate": 0.45},
          ...
        ],
        "hit_rate_change_7d": float,  # (week avg) - (prev week avg)
        "anomaly": "degrading" | "improving" | "stable"
      },
      # brief/draft/editorial_lint...
    }
  }
  ```
- 이상 판정: 7일 이동평균 기준 히트율 20%p 이상 하락 시 `"degrading"`

#### 1.2 `collect_citations_signals(since_days)` — citations cross-check 품질
- 소스: `logs/editorial_lint_*.json`의 `items[id=citations-cross-check]` 필드 또는 TASK_045 citations 관련 로그
- 반환:
  ```python
  {
    "checks_total": int,
    "by_status": {"pass": int, "warn-missing": int, "warn-mismatch": int, "fail": int},
    "top_mismatched_article_ids": [ ... ],  # warn-mismatch 빈도 상위 5건
    "trend_14d": [{"date": "...", "pass": 3, "warn": 1, "fail": 0}, ...],
    "anomaly": "mismatch_rising" | "stable" | "improving"
  }
  ```

#### 1.3 `collect_illustration_signals(since_days)` — 이미지 provider·비용
- 소스: `logs/illustrations.jsonl` (TASK_047 `provider_chain` 필드 포함)
- 반환:
  ```python
  {
    "provider_distribution": {"pollinations": 12, "placeholder": 3, "openai": 0},
    "fallback_rate": float,  # 원래 provider 실패해 chain 이동한 비율
    "monthly_cost_usd": float,
    "budget_utilization": float,  # monthly_cost / env MONTHLY_USD_CAP
    "fallback_reasons": {"rate_limit": 2, "auth": 0, "timeout": 1},
    "anomaly": "fallback_rising" | "budget_approaching" | "stable"
  }
  ```
- 이상 판정: fallback_rate > 20% 또는 budget_utilization > 0.8 시 anomaly 활성

#### 1.4 `collect_publish_monthly_signals(since_days)` — 발행 stage 텔레메트리
- 소스: `reports/publish_state_*.json` 파일들의 `telemetry` 섹션 (TASK_050)
- 반환:
  ```python
  {
    "recent_runs": [{"month": "2026-05", "stages_duration_sec": {...}, "stages_cost_usd": {...}}],
    "bottleneck_stage": "pdf_compile",  # 가장 느린 stage
    "stage_duration_change_7d": {  # stage별 추세
      "pdf_compile": "+15%",  # 지난주 대비
      "quality_gate": "-3%",
    },
    "anomaly": "bottleneck_worsening" | "stable"
  }
  ```

#### 1.5 `collect_failures()` 확장
기존 7 섹션 유지 + 신규 4 섹션 병합:
```python
return {
    "period": ...,
    # 기존
    "editorial_lint_failures": ...,
    "factcheck_summary": ...,
    "standards_failures": ...,
    "editor_corrections": ...,
    "langfuse_anomalies": ...,
    "total_articles": ...,
    # 신규 (TASK_053)
    "cache_signals": collect_cache_signals(since_days),
    "citations_signals": collect_citations_signals(since_days),
    "illustration_signals": collect_illustration_signals(since_days),
    "publish_monthly_signals": collect_publish_monthly_signals(since_days),
}
```

### Phase 2: sop_updater 프롬프트 확장 (15분)

[pipeline/sop_updater.py](../pipeline/sop_updater.py)의 `_summarize_failures()` + Opus system prompt 조정:

- 신규 4 섹션도 요약에 포함 (limit_chars 18000 초과 시 절삭 정책 유지)
- system prompt에 "운영 신호 4종 이상 징후는 프롬프트 수정이 아닌 **운영 결정 제안**으로 분류" 가이드 추가
  - 예: "cache 히트율 하락 → prompt 템플릿 재검토" vs "illustration fallback 상승 → 기본 provider 교체 검토"
- 기존 proposal 스키마(`patterns`·`updates`·`checklist`)는 **유지**, 신규 섹션 항목도 같은 스키마로 분류

### Phase 3: weekly_improvement 리포트 렌더 확장 (15분)

[scripts/weekly_improvement.py](../scripts/weekly_improvement.py)의 `_render_summary()` + `_render_checklist()`:

- `_render_summary`에 신규 4 섹션 헤드라인 추가:
  ```markdown
  ## 운영 신호 요약 (TASK_053)

  ### Cache
  - fact_checker 히트율: 45.9% → 42.1% (7일 변동 -3.8%p) ⚠️
  
  ### Citations
  - cross-check warn-mismatch 누적: 8건 (지난주 3건)
  
  ### Illustration
  - fallback rate: 12% / 월 누적 $0 / 상한 $0
  
  ### Publish Monthly
  - 최근 발행: 2026-05 / pdf_compile 병목: +15% vs 지난주
  ```
- `_render_checklist`에 신규 카테고리 `operations` 추가 (patterns·updates·checklist 기존 유지)

### Phase 4: pytest 확장 (10분)

- `tests/test_failure_collector.py` 신규 파일 (또는 기존 통합 테스트 확장):
  - 각 수집 함수 4종에 대해 최소 pass + anomaly 케이스
  - mock 로그 파일로 입력 제공
- `tests/test_sop_updater_prompt.py` 신규 파일 (선택):
  - Mock Anthropic 응답으로 신규 섹션 처리 여부 검증

기존 38 tests + 신규 6~8 tests 기대. 커버리지 목표: failure_collector **≥70%** (신규 목표 설정).

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| 로그 파일이 희박할 때 anomaly 판정 오작동 | 최소 샘플 수(예: 3일치 이상) 미달 시 `"insufficient_data"` 반환 |
| sop_updater 프롬프트 길이 초과 | 기존 `_summarize_failures(limit_chars=18000)` 절삭 정책 유지, 신규 섹션은 **요약만** (원본 JSON 제외) |
| 신규 섹션이 기존 patterns/updates 제안 품질을 희석 | system prompt에 "운영 신호는 별도 `operations` 카테고리로 분리" 명시 |
| 로그 파일 경로 Windows/Linux 차이 | 모든 경로는 `Path(__file__).parent / ...` 패턴 유지 (CLAUDE.md 코딩 규칙) |
| Langfuse·Ghost API 미설정 환경 | 기존 `collect_langfuse_anomalies`의 가드 패턴 재사용 (빈 리스트 반환) |
| 자동 판정이 편집자 결정 대체하려는 경향 | proposal 스키마에 **"편집자 승인 필수"** 마크 유지 — 자동 반영 금지 (TASK_027 원칙) |

---

## 무료 발행 원칙 정합성
- 본 태스크는 **내부 데이터 소비** — 외부 API 호출 추가 없음
- sop_updater의 Opus 호출은 기존 TASK_027·044에 포함된 것 — 추가 비용 없음
- 리포트는 로컬 markdown 파일만 생성

---

## 완료 조건 (Definition of Done)
- [ ] `failure_collector.py`에 4 신규 수집 함수 추가
- [ ] `collect_failures()` 반환 dict에 신규 4 섹션 포함
- [ ] `sop_updater.py` system prompt에 운영 신호 분류 가이드 추가
- [ ] `weekly_improvement.py` 리포트에 "운영 신호 요약" 섹션 렌더
- [ ] insufficient_data 가드 동작 (샘플 부족 시)
- [ ] anomaly 판정 스모크 (각 신호 1건씩 실제 로그 기반 테스트)
- [ ] pytest 커버리지 유지 또는 상승 (`failure_collector ≥70%` 목표)
- [ ] CLAUDE.md 코딩 규칙 준수 (request_id 로깅, UTF-8 Windows)
- [ ] 기존 TASK_027 루프 회귀 없음 (reports/improvement_*.md 기존 포맷 호환)

---

## 산출물
- `pipeline/failure_collector.py` (확장)
- `pipeline/sop_updater.py` (프롬프트·요약 확장)
- `scripts/weekly_improvement.py` (리포트 섹션 추가)
- `tests/test_failure_collector.py` (신규)
- `tests/test_sop_updater_prompt.py` (선택)
- `reports/task053_smoke_<date>.md` — 신규 섹션 포함된 샘플 improvement 리포트

---

## 후속 태스크 후보
- **TASK_054 후보**: failure_playbook 3회 반복 실패 → weekly_improvement auto-trigger (TASK_051 문서 후속 약속)
- **TASK_055 후보**: editor_corrections 기반 editorial_lint heuristic 자동 학습 (안전장치 포함)
- **TASK_056 후보**: 운영 신호 → Slack/이메일 실시간 알림 (budget·fallback·bottleneck)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_053 implemented
python codex_workflow.py update TASK_053 merged
```
