# TASK_055 — arXiv ingester (외부 큐레이션 L1 어댑터 신규)

## 메타
- **status**: todo
- **prerequisites**: TASK_032 (source_ingester.py RSS 어댑터)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화)

---

## 목적

매거진 5월 호 Deep Dive #5 (`arxiv-claude-research` 4p) 본문 source로 arXiv cs.AI 카테고리 4월 신규 논문을 자동 수집·필터링.

기존 `pipeline/source_ingester.py`는 RSS 어댑터만 보유. arXiv API는 RSS와 다른 형식(Atom + XML 메타데이터)이라 별도 어댑터 필요.

## 해결하는 운영 상황

- 매거진 Deep Dive 카테고리 본문에 "이 달의 Claude 관련 논문 5선" 자동 큐레이션
- arXiv 검색 쿼리: `claude OR anthropic OR "constitutional ai" OR "rlhf"`
- 매월 평균 50~100건 → keyword_filter (TASK_055 결과) → TOP 5 선정

## 구현 단계

### 1. `pipeline/ingesters/arxiv.py` 신규
```python
"""arXiv API 어댑터 (외부 큐레이션 L1).

사용법:
    from pipeline.ingesters.arxiv import fetch_recent_papers
    papers = fetch_recent_papers(
        query="claude OR anthropic OR constitutional ai",
        category="cs.AI",
        since_days=30,
        max_results=100,
    )
"""
import urllib.request
import xml.etree.ElementTree as ET

ARXIV_API_BASE = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}

def fetch_recent_papers(query, category="cs.AI", since_days=30, max_results=100):
    """반환: List[dict] — title, abstract, authors, link, published, arxiv_id"""
    # 1. URL 조합 (search_query + sortBy=submittedDate + sortOrder=descending)
    # 2. urllib.request.urlopen + 15s timeout
    # 3. ET 파싱 → 결과 dict 변환
    # 4. since_days 필터링 (published < now - since_days 제외)
    # 5. 반환
    ...
```

### 2. `config/feeds.yml`에 arXiv 항목 추가 (이미 있음, enabled true 변경)
```yaml
- name: "arXiv cs.AI (Claude 키워드)"
  type: arxiv  # 신규 type
  query: "claude OR anthropic OR constitutional+ai"
  category: cs.AI
  language: en
  stance: neutral
  is_official: true
  rights_status: free  # CC BY 4.0
  topics: [arxiv, papers, claude, ai_research]
  enabled: true
```

### 3. `pipeline/source_ingester.py` 확장
- `feed_type == "arxiv"` 분기 추가
- `pipeline.ingesters.arxiv.fetch_recent_papers()` 호출
- 각 paper를 `add_source()`로 source_registry에 등록 (rights_status: free)

### 4. CLI 명령 신규
```bash
python pipeline/ingesters/arxiv.py --query "claude" --since-days 30 --max-results 50 --dry-run
```

### 5. 단위 테스트 `tests/test_arxiv_ingester.py`
- `test_fetch_recent_papers_returns_list`
- `test_keyword_filter_excludes_non_claude`
- `test_since_days_filtering`
- `test_arxiv_id_format` (e.g., "2511.02824")
- `test_korean_encoding_safe` (논문 제목·초록 UTF-8)

## 완료 조건

- [ ] `pipeline/ingesters/arxiv.py` 모듈 신규
- [ ] `config/feeds.yml` arxiv 항목 enabled
- [ ] `pipeline/source_ingester.py` arxiv type 분기 처리
- [ ] dry-run으로 4월 논문 50건+ 수집 확인
- [ ] source_registry에 등록 시 rights_status: free + language: en + is_official: true
- [ ] 단위 테스트 5건 pass
- [ ] ruff clean / mojibake clean

## 후속

- TASK_058 (auto_summarizer L3)이 본 ingester 결과를 입력으로 받아 Sonnet 4.6으로 요약
- TASK_059 (monthly_curator L4)가 Sonnet 요약을 Opus 4.7로 클러스터링 → 매거진 Deep Dive #5 본문 입력

## 완료 처리

```bash
python codex_workflow.py update TASK_055 implemented
python codex_workflow.py update TASK_055 merged
```
