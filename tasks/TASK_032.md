# TASK_032 — 소스 자동 수집 파이프라인 (RSS·Atom Ingest)

## 메타
- **status**: todo
- **prerequisites**: TASK_004 (source_registry.py)
- **예상 소요**: 90분
- **서브에이전트 분할**: 불필요
- **Phase**: 5 확장 (WorldMonitor 시너지)

---

## 목적
WorldMonitor "500+ 뉴스 피드 자동 집계" 패턴 차용.
현재 파이프라인 최대 병목인 **편집자 수동 소스 수집**을 자동화.

리포트 인용: _"Cross-stream correlation — 500+ feeds → AI briefs. 단편 신호보다 수렴 분석이 핵심."_

편집자 흐름 변화:
- Before: 편집자가 URL 수집 → `--sources file1.md` 지정 → brief_generator
- After: RSS 자동 수집 → 주간 피드 대시보드 → 주제 선정 → brief_generator

---

## 구현 명세

### 1. 생성 파일
```
pipeline/
└── source_ingester.py         ← RSS/Atom 수집 + Haiku 분류 + 등록

scripts/
└── run_source_ingest.py       ← Cron 진입점

config/
└── feeds.yml                   ← 구독 피드 목록

n8n/
└── workflow_6_source_ingest.json  ← 매일 05:00 KST

data/
└── source_ingest_state.json   ← 마지막 수집 timestamp (gitignore)
```

### 2. `config/feeds.yml` 스키마

```yaml
feeds:
  - name: "Anthropic Blog"
    url: "https://www.anthropic.com/news/feed.xml"
    language: en         # ko | en | ja | zh
    stance: neutral      # pro | neutral | con
    is_official: true
    topics: [claude, ai_models]
    enabled: true

  - name: "KISA 보도자료"
    url: "https://www.kisa.or.kr/rss/press.xml"
    language: ko
    stance: neutral
    is_official: true
    topics: [ai_regulation, privacy]
    enabled: true
```

### 3. `pipeline/source_ingester.py` 핵심 함수

```python
def ingest_feeds(
    feeds_path: str = "config/feeds.yml",
    since_days: int | None = None,
    feed_filter: str | None = None,
    dry_run: bool = False,
    auto_classify: bool = True,
) -> dict:
    """
    반환: {
        "period": {"from", "to"},
        "feeds_processed": int,
        "entries_fetched": int,
        "entries_new": int,
        "entries_duplicate": int,
        "entries_registered": int,
        "entries_skipped": int,
        "details": [
            {"feed": str, "new": int, "dup": int, "errors": []},
        ],
    }
    """

def fetch_feed(url: str, timeout: int = 15) -> list[dict]:
    """feedparser로 RSS/Atom 파싱. 반환: entries list"""

def filter_new_entries(entries: list[dict], feed_name: str, since: datetime) -> list[dict]:
    """published_at > state[feed_name] 인 entry만"""

def classify_entry(title: str, summary: str, feed_config: dict) -> dict:
    """
    Haiku 4.5 호출 (선택):
    - topic 자동 분류 (feed 설정의 topics + 추출된 키워드)
    - relevance_score 0~1
    API 키 없으면 graceful fallback (feed.topics 그대로 사용)
    """

def detect_duplicate(entry_url: str) -> str | None:
    """source_registry에 이미 URL 존재하면 source_id 반환"""
```

### 4. CLI (`scripts/run_source_ingest.py`)

```bash
# 전체 피드 수집 (기본)
python scripts/run_source_ingest.py

# 특정 피드만
python scripts/run_source_ingest.py --feed "Anthropic Blog"

# 드라이런 (등록 없이 조회만)
python scripts/run_source_ingest.py --dry-run

# 마지막 N일 강제 재수집
python scripts/run_source_ingest.py --since-days 7

# Haiku 분류 skip (비용 절감)
python scripts/run_source_ingest.py --no-classify
```

### 5. State 파일 (`data/source_ingest_state.json`)

Idempotent 수집 위한 상태:
```json
{
  "Anthropic Blog": "2026-04-22T09:00:00Z",
  "OpenAI Blog": "2026-04-21T12:00:00Z"
}
```
- 기본: 각 피드별 마지막 수집 시각 이후만 수집
- `--since-days N`: state 무시하고 N일 전부터

### 6. 중복 제거 로직

1. **URL 완전 일치** (1차): `source_registry.add_source()` 자체가 idempotent — 기존 URL이면 기존 source_id 반환
2. **제목 유사도** (2차, 선택): 80% 이상 유사하면 스킵
3. 신규 등록만 카운트

### 7. 출력 형식

```
=== 소스 자동 수집 ===
기간: 2026-04-15T00:00:00Z ~ 2026-04-22T09:00:00Z
피드 수: 5

[1/5] Anthropic Blog
  📥 12건 조회 / 3건 신규 / 9건 기존
  - "Claude 4.6 Sonnet 출시" → topics=[claude, ai_models]
  - "Context Caching 확장" → topics=[claude, pricing]
  - "Agent SDK 업데이트" → topics=[claude, agents]

[2/5] OpenAI Blog
  ⏭  0건 신규

[3/5] KISA 보도자료
  📥 4건 조회 / 2건 신규
  ...

=== 결과 ===
5 피드 / 31 조회 / 8 신규 / 23 기존
등록 완료: source_registry.db (127 → 135)
상태 저장: data/source_ingest_state.json
```

### 8. n8n workflow_6

- Cron: 매일 05:00 KST
- Execute Command: `python scripts/run_source_ingest.py`
- Slack Notify (신규 5건 이상일 때만): "주간 피드 {N}건 신규 수집"
- Error Trigger → Slack 에러 알림

### 9. requirements.txt 추가
```
feedparser>=6.0.0
```

### 10. `.gitignore` 추가
```
data/source_ingest_state.json
```

---

## 완료 조건
- [ ] `pipeline/source_ingester.py` 구현
- [ ] `scripts/run_source_ingest.py` CLI 진입점
- [ ] `config/feeds.yml` 초기 피드 목록 (5개 이상 실제 RSS URL)
- [ ] `n8n/workflow_6_source_ingest.json` 생성
- [ ] `requirements.txt`에 feedparser 추가
- [ ] `.gitignore`에 state 파일 제외
- [ ] 스모크 테스트: `--dry-run` 실행 시 실제 네트워크 호출 없이 구조 검증
- [ ] 실제 1개 피드 수집 성공 (피드 URL 유효한 것)
- [ ] 중복 URL 재등록 시 기존 source_id 반환 확인
- [ ] Windows UTF-8 출력 깨짐 없음

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_032 implemented
```

## 주의사항
- RSS 호출 timeout=15, 실패 시 해당 피드만 skip (전체 실패 금지)
- Haiku 분류 실패 시 `feed.topics` 그대로 사용 (graceful)
- `content_preview`는 150자로 제한 (registry 용량 관리)
- 피드 URL이 유효하지 않으면 details에 error 기록하고 계속 진행
- state 파일 읽기 실패 시 전체 재수집으로 fallback
