# TASK_028 — 운영 투명성 대시보드 (Opacity to Transparency)

## 메타
- **status**: todo
- **prerequisites**: 없음 (TASK_008 Langfuse merged, 선택적 확장)
- **예상 소요**: 75분
- **서브에이전트 분할**: 가능 (A: 메트릭 수집기 / B: 대시보드 UI)
- **Phase**: 4 (운영 투명성)

---

## 목적
Miessler "Opacity to Transparency" 원칙 적용.

> "기업은 분위기와 스프레드시트로 운영" → 측정 가능한 개선으로 전환. 실제 비용, 소요 시간, 품질, **실제 작업 대 보조 작업 비율**.

현재 Langfuse는 API 호출만 추적. **인간 시간·기사당 총 비용·품질 이탈률 미측정**.

---

## 구현 명세

### 1. 생성 파일
```
pipeline/
└── metrics_collector.py         ← 다중 소스 메트릭 통합

web/src/pages/
└── DashboardPage.jsx             ← React 대시보드

scripts/
└── export_metrics.py             ← JSON/CSV 내보내기
```

### 2. 측정 항목 (5개 카테고리)

**A. 비용 (Cost)**
- 기사당 API 비용 ($/article) — brief·draft·factcheck·channel 합산
- 월 누적 API 비용
- 모델별 비용 분포 (Sonnet / Opus / Haiku)
- 재시도·실패 호출 비용 (낭비)

**B. 시간 (Time)**
- 기사당 AI 처리 시간 (합산)
- 기사당 편집자 시간 (수동 입력 or git timestamp 추정)
- **AI:인간 시간 비율** ⭐ Miessler 핵심 지표
- 발행 리드타임 (topic 선정 → 게시)

**C. 품질 (Quality)**
- editorial_lint 통과율
- standards_checker 통과율 (TASK_025)
- 팩트체크 실패율 (과장·수치·출처 부족)
- 편집자 수정 빈도 (corrections per article, TASK_026)

**D. 도달 (Reach)**
- Ghost 오픈율 (API 조회)
- CTR (클릭률)
- 구독자 증감 (net new subscribers)
- 채널별 재가공 산출물 수

**E. 운영 (Operations)**
- n8n 워크플로우 실행 수 / 성공률
- 실패 알림 수
- 커버 이미지 등록률
- SNS 자산 등록률

### 3. `pipeline/metrics_collector.py` 시그니처

```python
def collect_metrics(
    since_days: int = 30,
    article_id: str | None = None,
) -> dict:
    """
    다중 소스 통합:
    - logs/ (Claude API request_id·usage)
    - data/editor_corrections.db (TASK_026)
    - Langfuse API (있으면)
    - Ghost Content API (post analytics)
    - git log (editor time 추정)

    반환: {
        "period": {"from", "to", "days"},
        "cost": {...},
        "time": {...},
        "quality": {...},
        "reach": {...},
        "operations": {...},
        "per_article": [  # 기사별 breakdown
            {"article_id", "category", "cost_usd", "ai_time_sec", "editor_time_sec",
             "ai_editor_ratio", "lint_pass", "open_rate", ...},
        ],
    }
    """

def estimate_editor_time(article_id: str) -> float:
    """
    git log 기반 추정:
    - drafts/article_id.md 첫 커밋 ~ 마지막 수정 사이 간격
    - 커밋 수 × 평균 세션 길이 추정 (가중치)
    반환: seconds
    """
```

### 4. `scripts/export_metrics.py`

```bash
# JSON export
python scripts/export_metrics.py --since-days 30 --format json --output metrics.json

# CSV (기사별 breakdown)
python scripts/export_metrics.py --since-days 30 --format csv --per-article > per_article.csv

# Markdown 요약 (월간 리포트용)
python scripts/export_metrics.py --since-days 30 --format md > monthly_report.md
```

### 5. React 대시보드 (`web/src/pages/DashboardPage.jsx`)

기존 웹 앱에 `/dashboard` 라우트 추가. 빌드 시 `metrics.json`을 정적으로 포함하거나, 개발 모드에서는 fetch.

**레이아웃:**
```
┌─────────────────────────────────────────────┐
│ 📊 Claude Magazine 운영 대시보드  (30일)    │
├─────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ AI:인간  │ │ 기사당   │ │ 월 누적  │    │
│ │ 시간비   │ │ API 비용 │ │ 비용    │    │
│ │  1:3.2   │ │  $0.42   │ │  $28    │    │
│ └──────────┘ └──────────┘ └──────────┘    │
│                                             │
│ 📈 기사당 비용 추이 (LineChart)             │
│ 📊 모델별 비용 분포 (PieChart)              │
│ 📉 editorial_lint 통과율 (BarChart)         │
│ 📰 기사별 상세 (DataTable)                  │
└─────────────────────────────────────────────┘
```

- Recharts 재사용 (기존 InsightPage 패턴)
- THEME 색상 그대로
- 상단 카드 3개 = Miessler 핵심 지표 (AI:Human ratio · $/article · monthly total)

### 6. 웹 빌드 통합

```jsx
// App.jsx의 PAGES 배열에 추가 (admin 모드에서만?)
const PAGES = ['표지', '기사', '인사이트', '인터뷰', '리뷰', '특집', '대시보드'];
```

또는 URL 파라미터 `?admin=1` 일 때만 노출.

### 7. Langfuse 통합 (선택)
`LANGFUSE_ENABLED=True` 이면 Langfuse API로 추가 메트릭 확보:
- 프롬프트 캐시 hit rate
- P50/P95/P99 latency
- Trace 내 retry 횟수

없으면 `logs/` 파일 파싱으로 대체.

---

## 완료 조건
- [ ] `pipeline/metrics_collector.py` 구현 (5개 카테고리)
- [ ] `scripts/export_metrics.py` (json/csv/md 3포맷)
- [ ] `web/src/pages/DashboardPage.jsx` 구현
- [ ] `App.jsx`에 대시보드 라우트 추가 (`?admin=1` 조건)
- [ ] AI:인간 시간 비율 **상단 카드 중앙 배치** (Miessler 핵심 지표)
- [ ] 스모크 테스트: `export_metrics.py --since-days 30` 성공 + 대시보드 정상 렌더
- [ ] Ghost/Langfuse 미연동 상태에서도 실패 없이 부분 데이터 반환
- [ ] 기사당 비용 추이 차트 (최근 30일) 정상 표시

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_028 implemented
```

## 주의사항
- editor_time 추정은 **근사치** (실제 타이머 미존재) — `estimated: true` 플래그 UI 노출
- git log 파싱은 `drafts/` 내부 파일만 대상 (published는 이미 Ghost로)
- Ghost Content API rate limit 주의 — 기사 많으면 캐시
- 대시보드는 **읽기 전용** — 설정 수정 기능 금지
- 민감 정보(API key, 편집자 이메일) 대시보드 노출 금지
- Recharts tooltip에 원화(KRW) 환산 표시 (1 USD = 실시간 환율 or 고정 $1=₩1,350)
