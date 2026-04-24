# TASK_048 — 운영 관측 위젯 (cache·citations·illustration provider)

## 메타
- **status**: todo
- **prerequisites**: TASK_028 (운영 투명성 대시보드), TASK_043 (illustration provider 라우팅), TASK_044 (Prompt Caching), TASK_045 (Citations API)
- **예상 소요**: 90분
- **서브에이전트 분할**: 가능 (Phase 1-2 백엔드 vs Phase 3 프론트엔드)
- **Phase**: 6 (운영 관측 강화)

---

## 목적
TASK_044·045·043에서 생성되는 신호가 **로그에만 쌓이고 운영 표면에 노출되지 않음**. 대시보드에 3 위젯을 추가해 ① cache 효과 정량 입증 ② citations 품질 모니터링 ③ illustration provider 사용·비용 가시화.

### 이번 phase가 해결하는 운영 질문
- Prompt Caching 효과가 실제로 나타나고 있는가? (히트율·비용 절감)
- Citations cross-check의 pass/warn/fail 비율이 어떻게 변화하는가? (→ 미래 TASK_048 warn→fail 승격 근거)
- illustration provider가 placeholder 외로 전환되었을 때 비용이 어느 수준인가?

---

## 구현 명세

### Phase 1: metrics_collector 확장 (40분)

신규 수집 대상 3종:

#### 1.1 cache 지표
[pipeline/metrics_collector.py](../pipeline/metrics_collector.py)의 로그 집계 경로에 추가:
- 소스: `logs/factcheck_*.json` (TASK_044 이후 `cache_creation_input_tokens`·`cache_read_input_tokens` 필드 있음)
- 집계:
  ```python
  {
    "cache": {
      "fact_checker": {
        "runs_with_cache_enabled": int,
        "total_cache_creation_tokens": int,
        "total_cache_read_tokens": int,
        "cache_hit_rate": float,  # read / (read + creation) in cached runs
        "estimated_saved_usd": float,  # (read * (base_rate - read_rate)) at Opus 4.7 rate
      },
      "other_pipelines": [  # editorial_lint, brief, draft — cache_enabled 대부분 false 예상
        {"pipeline": "brief_generator", "runs": int, "cache_enabled_runs": int}
      ]
    }
  }
  ```

#### 1.2 citations 지표
- 소스: `logs/editorial_lint_*.json` 또는 `reports/task045_*.json` (신규 집계 필요)
- 집계:
  ```python
  {
    "citations": {
      "article_runs_with_citations_check": int,
      "pass": int,
      "warn_missing": int,       # citations 파일 부재
      "warn_mismatch": int,      # manual source_id ≠ citations
      "fail": int,               # severity=fail로 승격됐을 때 사용 (현재는 0)
      "pass_rate": float,
      "trend_14d": [...]         # 14일치 일별 분포 (warn→fail 승격 판단용)
    }
  }
  ```

#### 1.3 illustration provider 지표
- 소스: `logs/illustrations.jsonl` (TASK_043이 이미 기록)
- 집계:
  ```python
  {
    "illustration": {
      "provider_distribution": {"placeholder": int, "openai": int, ...},
      "monthly_cost_usd": float,  # provider별 cost_estimate 합계
      "monthly_cost_by_provider": {"openai": float, ...},
      "budget_cap_usd": 5.0,      # env CLAUDE_MAGAZINE_ILLUSTRATION_MONTHLY_USD_CAP, default 5
      "budget_utilization": float  # 0.0 ~ 1.0+
    }
  }
  ```

### Phase 2: export_metrics.py 스키마 확장 (15분)

[scripts/export_metrics.py](../scripts/export_metrics.py)의 JSON·CSV·Markdown 출력에 위 3 섹션 포함. 기존 섹션(cost·time·quality·reach·operations·per_article) **회귀 없음**.

Markdown 포맷 예시:
```markdown
## Prompt Caching (7일)
- fact_checker cache hit rate: 78% (21/27 runs)
- 절감 추정: $4.32

## Citations Cross-Check
- pass: 18 / warn-missing: 2 / warn-mismatch: 4 / fail: 0
- 14일 추세: [보조 차트]

## Illustration Provider
- 사용 분포: placeholder 40, openai 0
- 월 누적 비용: $0.00 / 상한 $5.00 (utilization 0%)
```

### Phase 3: DashboardPage.jsx 위젯 3개 추가 (30분)

[web/src/pages/DashboardPage.jsx](../web/src/pages/DashboardPage.jsx) 확장. 기존 `EMPTY_METRICS`에 3 섹션 추가:
- `cache`, `citations`, `illustration` 필드 기본값
- 로딩 실패 시 기본값으로 graceful degrade (기존 패턴 유지)

위젯 구성 (기존 Panel/StatCard 재사용):
1. **Cache 효과 Panel** — StatCard(hit rate %), StatCard(절감 추정 USD), 선택적 LineChart (일별 hit rate)
2. **Citations 품질 Panel** — PieChart (pass/warn/fail 분포), 14일 BarChart (일별 추세)
3. **Illustration 비용 Panel** — StatCard(월 누적 USD / 상한), ProgressBar (utilization), BarChart (provider별 분포)

신규 탭 만들지 않음 — 대시보드 본문 하단에 3 패널 추가.

### Phase 4: 스모크 테스트 (5분)
- `python scripts/export_metrics.py --format markdown` 실행 → 신규 3 섹션 모두 출력되는지 확인
- `python scripts/export_metrics.py --format json` → 스키마 validation (신규 필드 존재)
- `cd web && npm run build` → 빌드 에러 없음

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| 로그 필드 이름 오타·부재로 집계 0 | `metrics_collector`에 fallback (`.get(field, 0)`), 테스트 로그 3건 준비 후 검증 |
| `logs/illustrations.jsonl` 경로 하드코딩 | [pipeline/illustration_hook.py](../pipeline/illustration_hook.py)의 `LOG_PATH` 상수 재사용 |
| 대시보드 렌더링 비용 상한 초과 시 경고 로직 누락 | `budget_utilization >= 0.8`일 때 위젯 색상 warning (THEME.warning 기존 토큰 활용) |
| 기존 대시보드 레이아웃 파손 | 기존 `EMPTY_METRICS` 키 보존, 신규 키만 추가 |
| 14일 추세 데이터 축적 전 빈 차트 | 데이터 부족 시 "데이터 축적 중" 플레이스홀더 |

---

## 완료 조건 (Definition of Done)
- [ ] `metrics_collector.py`에 cache·citations·illustration 집계 함수 3개 추가
- [ ] `export_metrics.py` JSON 출력에 신규 3 섹션 포함
- [ ] `export_metrics.py` Markdown 출력에 신규 3 섹션 포함
- [ ] CSV 출력은 기존 per_article 중심 유지 (신규 섹션 선택 사항)
- [ ] `DashboardPage.jsx`에 3 위젯 추가, 기존 위젯 회귀 없음
- [ ] budget_utilization >= 0.8일 때 warning 색상 적용
- [ ] `npm run build` 에러 없음
- [ ] `reports/task048_smoke_<date>.md` 작성 (샘플 metrics.json + 스크린샷 또는 markdown 출력)
- [ ] TASK_045 severity=warn→fail 승격 판단에 쓸 수 있는 14일 추세 데이터 필드 존재

---

## 산출물
- `pipeline/metrics_collector.py` (확장)
- `scripts/export_metrics.py` (JSON·Markdown 신규 섹션)
- `web/src/pages/DashboardPage.jsx` (3 위젯 추가)
- `reports/task048_smoke_<date>.md` (신규)

---

## 후속 태스크 후보
- **TASK_050 후보**: citations severity warn→fail 승격 (본 태스크 데이터 14일 축적 후 재검토)
- **TASK_051 후보**: 운영 알림 (budget_utilization >= 1.0 시 Slack 통지) — TASK_028 알림 채널 재사용

---

## 완료 처리
```bash
python codex_workflow.py update TASK_048 implemented
python codex_workflow.py update TASK_048 merged
```
