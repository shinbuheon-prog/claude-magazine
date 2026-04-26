# TASK_057 — Reddit OAuth ingester (r/ClaudeAI 등)

## 메타
- **status**: todo
- **prerequisites**: TASK_032 (source_ingester.py)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화)

---

## 목적

매거진 5월 호 Insight #9 (`hn-reddit-april-topics` 3p) 본문 source로 Reddit r/ClaudeAI·r/LocalLLaMA·r/MachineLearning에서 Claude·Anthropic 키워드 인기 게시글을 자동 수집.

Reddit OAuth API는 **무료 + Client ID 등록 필수 (즉시 발급)**. 외부 OSS [dansholds/menshun](https://github.com/dansholds/menshun)의 Aho-Corasick 키워드 매칭 알고리즘 차용 (대량 키워드 효율 검색).

## 해결하는 운영 상황

- 매거진 Insight 카테고리 본문에 r/ClaudeAI 인기 토픽 자동 큐레이션
- Reddit API 쿼리: `subreddit:ClaudeAI+OR+subreddit:LocalLLaMA+OR+subreddit:MachineLearning&q=claude`
- 매월 평균 50~150건 → keyword_filter (TF-IDF 보강) → 점수·댓글 수 정렬 → TOP 10
- HN과 통합 (TASK_056 결과와 합침) → "Insight #9 본문 입력"

## 인증 설정 (편집자 액션 1회)

1. https://www.reddit.com/prefs/apps 접속
2. "create another app" → script type 선택
3. name: `claude-magazine-curator`, redirect uri: `http://localhost`
4. 발급된 Client ID·Secret을 `.env`에 저장:
```bash
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT="claude-magazine/0.3 by /u/<username>"
```

## 구현 단계

### 1. `pipeline/ingesters/reddit.py` 신규
```python
"""Reddit OAuth API 어댑터 (외부 큐레이션 L1).

API: https://www.reddit.com/dev/api
무료, OAuth 2.0 Client Credentials, rate limit 60 req/min

사용법:
    from pipeline.ingesters.reddit import fetch_top_posts
    posts = fetch_top_posts(
        subreddits=["ClaudeAI", "LocalLLaMA", "MachineLearning"],
        keywords=["claude", "anthropic", "mcp"],
        since_days=30,
        min_score=20,
        max_results=50,
    )
"""
import os
import urllib.request
import json
from datetime import datetime, timezone, timedelta

REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"

def _get_oauth_token():
    """Client Credentials로 OAuth 토큰 발급 (1시간 유효)."""
    client_id = os.environ["REDDIT_CLIENT_ID"]
    client_secret = os.environ["REDDIT_CLIENT_SECRET"]
    user_agent = os.environ["REDDIT_USER_AGENT"]
    # POST /api/v1/access_token with Basic Auth + grant_type=client_credentials
    ...

def fetch_top_posts(subreddits, keywords, since_days=30, min_score=20, max_results=50):
    """반환: List[dict] — title, selftext, url, permalink, score, num_comments, author, subreddit, created_at"""
    token = _get_oauth_token()
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    results = []
    for sub in subreddits:
        # GET /r/{sub}/top?t=month&limit=100
        # Authorization: Bearer {token}
        # 키워드 매칭 (Aho-Corasick 또는 단순 lowercase substring)
        # min_score · cutoff 필터링
        ...
    return results[:max_results]
```

### 2. `config/feeds.yml`에 Reddit 항목 추가
```yaml
- name: "Reddit r/ClaudeAI (Claude 키워드)"
  type: reddit
  subreddits: [ClaudeAI, LocalLLaMA, MachineLearning]
  query: "claude OR anthropic OR mcp"
  language: en
  stance: neutral
  is_official: false
  rights_status: free  # 200자 인용 + author 표기
  quote_limit: 200  # Reddit ToS 준수
  topics: [reddit, claude, ai_news, community]
  enabled: false  # 편집자가 .env 키 입력 후 활성화
```

### 3. `pipeline/source_ingester.py` 확장
- `feed_type == "reddit"` 분기
- `add_source()` 호출 시 publisher 형식: `"Reddit r/{subreddit} ({author})"`
- url 필드는 Reddit permalink (`https://reddit.com{permalink}`) 사용

### 4. CLI 명령
```bash
python pipeline/ingesters/reddit.py --subreddit ClaudeAI --since-days 30 --min-score 20 --dry-run
```

### 5. 단위 테스트 `tests/test_reddit_ingester.py`
- `test_oauth_token_request_format` (mock urllib)
- `test_keyword_filter_aho_corasick`
- `test_min_score_filter`
- `test_quote_limit_200_default` (governance 준수)
- `test_user_agent_required` (Reddit ToS — User-Agent 누락 시 차단)
- `test_korean_encoding_safe`

## 완료 조건

- [ ] `pipeline/ingesters/reddit.py` 모듈 신규
- [ ] `.env.example`에 REDDIT_* 3 환경변수 추가
- [ ] `config/feeds.yml` reddit 항목 (enabled: false 기본)
- [ ] `pipeline/source_ingester.py` reddit type 분기
- [ ] dry-run으로 r/ClaudeAI 4월 20건+ 수집 확인
- [ ] 단위 테스트 6건 pass
- [ ] ruff clean / mojibake clean
- [ ] User-Agent 누락 시 명확한 에러 메시지

## 후속

- TASK_058 (auto_summarizer)이 Reddit 게시글 + selftext를 Sonnet 4.6으로 요약
- TASK_059 (monthly_curator)가 HN + Reddit 통합 → Insight #9 본문 입력

## 주의사항 (Reddit ToS)

- User-Agent 필수 (없으면 차단 + 비공식 도구 분류)
- Rate limit 60 req/min 준수 (서브레딧당 1초 지연 권장)
- 인용 시 author + permalink 표기 의무
- 사용자 ID 비식별화 (governance.md §"개인정보 처리 원칙")

## 완료 처리

```bash
python codex_workflow.py update TASK_057 implemented
python codex_workflow.py update TASK_057 merged
```
