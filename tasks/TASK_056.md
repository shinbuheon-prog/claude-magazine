# TASK_056 — Hacker News Algolia API ingester

## 메타
- **status**: todo
- **prerequisites**: TASK_032 (source_ingester.py)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화)

---

## 목적

매거진 5월 호 Insight #9 (`hn-reddit-april-topics` 3p) 본문 source로 Hacker News에서 Claude·Anthropic·MCP 키워드 인기 스레드를 자동 수집.

HN Algolia Search API는 무료 + 인증 불필요 + 키워드·날짜·점수·댓글 수 필터 지원. 외부 OSS [santiagobasulto/python-hacker-news](https://github.com/santiagobasulto/python-hacker-news) 패턴 차용 가능.

## 해결하는 운영 상황

- 매거진 Insight 카테고리 본문에 "4월 r/ClaudeAI·HN에서 가장 많이 언급된 문제 TOP 10" 자동 큐레이션
- HN Algolia API 쿼리: `query=claude+OR+anthropic+OR+mcp&numericFilters=created_at_i>{epoch}`
- 매월 평균 30~80건 → keyword_filter → 점수·댓글 수 정렬 → TOP 10

## 구현 단계

### 1. `pipeline/ingesters/hackernews.py` 신규
```python
"""Hacker News Algolia API 어댑터 (외부 큐레이션 L1).

API: https://hn.algolia.com/api/v1/search
무료, 인증 불필요, rate limit 10,000 req/h (실용상 무제한)

사용법:
    from pipeline.ingesters.hackernews import fetch_top_stories
    stories = fetch_top_stories(
        query="claude OR anthropic OR mcp",
        since_days=30,
        min_points=10,
        max_results=50,
    )
"""
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone, timedelta

HN_API_BASE = "https://hn.algolia.com/api/v1/search"

def fetch_top_stories(query, since_days=30, min_points=10, max_results=50):
    """반환: List[dict] — title, url, points, num_comments, author, created_at, story_id"""
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp())
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"points>={min_points},created_at_i>{cutoff}",
        "hitsPerPage": min(max_results, 1000),
    }
    # 1. URL 조합 + urllib.request.urlopen (15s timeout)
    # 2. JSON 파싱
    # 3. hits 배열을 표준 형식으로 변환
    # 4. 점수·댓글 수 정렬 → 반환
    ...
```

### 2. `config/feeds.yml`에 HN 항목 추가
```yaml
- name: "Hacker News (Claude 키워드)"
  type: hackernews
  query: "claude OR anthropic OR mcp"
  language: en
  stance: neutral
  is_official: false
  rights_status: free  # 댓글 fair use 100자 한도
  quote_limit: 100  # HN 댓글 인용 한도
  topics: [hackernews, claude, ai_news, community]
  enabled: true
```

### 3. `pipeline/source_ingester.py` 확장
- `feed_type == "hackernews"` 분기 추가
- 각 story를 `add_source()`로 등록 (publisher: "Hacker News (HN)", quote_limit: 100)
- url 필드는 HN story URL (`https://news.ycombinator.com/item?id={story_id}`) 사용 (외부 링크는 별도 메타데이터)

### 4. CLI 명령 신규
```bash
python pipeline/ingesters/hackernews.py --query "claude" --since-days 30 --min-points 10 --dry-run
```

### 5. 단위 테스트 `tests/test_hackernews_ingester.py`
- `test_fetch_top_stories_returns_list`
- `test_min_points_filter`
- `test_since_days_filter`
- `test_keyword_filter_in_title`
- `test_quote_limit_default_100` (governance.md 준수)

## 완료 조건

- [ ] `pipeline/ingesters/hackernews.py` 모듈 신규
- [ ] `config/feeds.yml` hackernews 항목 enabled
- [ ] `pipeline/source_ingester.py` hackernews type 분기
- [ ] dry-run으로 4월 30건+ 수집 확인 (Claude 키워드, points >= 10)
- [ ] 단위 테스트 5건 pass
- [ ] ruff clean / mojibake clean
- [ ] HN 댓글 인용 시 quote_limit 100 강제 (editorial_lint와 정합)

## 후속

- TASK_058 (auto_summarizer)이 HN story + 댓글 트리를 Sonnet 4.6으로 요약
- TASK_059 (monthly_curator)가 토픽 클러스터링 → Insight #9 본문 (mckinsey-pptx KPI dashboard 연결)

## 완료 처리

```bash
python codex_workflow.py update TASK_056 implemented
python codex_workflow.py update TASK_056 merged
```
