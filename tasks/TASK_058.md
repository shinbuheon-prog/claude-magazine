# TASK_058 — pipeline/auto_summarizer.py L3 (Sonnet/Haiku 자동 요약)

## 메타
- **status**: todo
- **prerequisites**: TASK_055·TASK_056·TASK_057 (3 ingester 모두 완료)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화)

---

## 목적

외부 큐레이션 파이프라인 5계층 중 **L3 자동 요약** 계층 신규.

source_registry에 등록된 raw source (arXiv 논문 abstract / HN story 제목·본문 / Reddit 게시글 selftext)를 Sonnet 4.6 또는 Haiku 4.5로 자동 요약 → 매거진 brief_generator 입력으로 직접 사용 가능한 형태로 변환.

[docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §5 권장 형식 채택.

## 해결하는 운영 상황

- 매거진 5월 호 Deep Dive #5·#6·#7 + Insight #9 본문 작성 시 raw source 50~100건을 편집장이 직접 읽기 부담
- 자동 요약 1줄 + 3줄 + 키 인용 (≤200자) 자동 생성 → 편집장은 요약 검토 후 매거진 본문에 인용 또는 plan_issue brief_input으로 전달
- 인용 한도 200자 자동 검증 + truncate (governance.md §"개인정보 처리 원칙" + source_policy.md)

## 구현 단계

### 1. `pipeline/auto_summarizer.py` 신규
```python
"""외부 source 자동 요약 (외부 큐레이션 L3 계층).

3 단계 요약:
  1. summary_oneliner: Haiku 4.5, 제목 + 본문 첫 500자 → 1줄
  2. summary_3line: Sonnet 4.6, 본문 전체 → 3줄
  3. key_quotes: Sonnet 4.6, 본문 전체 → JSON list, 각 quote ≤ 200자 (자체 콘텐츠 예외)

사용:
    from pipeline.auto_summarizer import summarize_source, batch_summarize_pending

    # 단일 source
    result = summarize_source(source_id="...", levels=["oneliner", "3line", "quotes"])

    # source_registry 미요약 source 일괄 처리
    results = batch_summarize_pending(article_id_filter=None, max_count=100)

CLI:
    python pipeline/auto_summarizer.py --article-id monthly_digest_2026-04-W3 --max-count 30
    python pipeline/auto_summarizer.py --source-id sns-blog-20260421-... --levels oneliner,3line
"""
import os
import sqlite3
from anthropic import Anthropic

ROOT = ...
DB_PATH = ...

# Sonnet 4.6 + Haiku 4.5 프롬프트 (prompts/template_*.txt 참조)
PROMPT_ONELINER_HAIKU = """제목: {title}

본문 (첫 500자):
{body_preview}

위 source를 1줄(50자 이내)로 요약하라. 한국어 우선.
출력은 요약 1줄만 (메타데이터·따옴표 금지).
"""

PROMPT_3LINE_SONNET = """제목: {title}

본문 전체:
{body}

위 source를 한국어 3줄로 요약하라:
1. 핵심 변화·발견 (1줄)
2. 왜 중요한가 (1줄)
3. 매거진 활용 각도 (1줄)
"""

PROMPT_QUOTES_SONNET = """제목: {title}

본문 전체:
{body}

위 source에서 매거진 본문 인용에 적합한 짧은 인용구 3~5개를 추출하라:
- 각 인용 ≤ 200자 (governance.md 인용 한도 준수)
- 한국어 또는 원문 그대로
- JSON list 형식: [{{"quote": "...", "context": "...", "page_or_section": "..."}}, ...]

자체 콘텐츠(rights_status: free)는 한도 초과 가능 — 그래도 200자 이하 권장.
"""

def summarize_source(source_id, levels=("oneliner", "3line", "quotes")):
    """source_registry 1건 요약 + DB 갱신.

    반환: {source_id, summary_oneliner, summary_3line, key_quotes, total_tokens, request_id}
    """
    # 1. source_registry에서 source 조회 (url, title, raw_text 또는 content_preview)
    # 2. levels 별 LLM 호출:
    #    - oneliner → Haiku 4.5 (input ~500토큰, output ~50토큰)
    #    - 3line → Sonnet 4.6 (input ~5000토큰, output ~150토큰)
    #    - quotes → Sonnet 4.6 (input ~5000토큰, output ~500토큰)
    # 3. request_id 추출 → logs/auto_summarizer_{date}.json 저장 (CLAUDE.md 규칙)
    # 4. source_registry 신규 컬럼 update (alter table 마이그레이션 — TASK_019 패턴):
    #    - summary_oneliner TEXT
    #    - summary_3line TEXT
    #    - key_quotes TEXT (JSON)
    #    - summarized_at TEXT (ISO8601)
    # 5. 인용 한도 자동 검증 (key_quotes 각 항목 > 200자 → truncate + warning)
    # 6. 결과 dict 반환

def batch_summarize_pending(article_id_filter=None, max_count=100):
    """미요약 source 일괄 처리 (summary_oneliner IS NULL 조건).

    반환: List[dict]
    """
    ...
```

### 2. `pipeline/source_registry.py` 스키마 마이그레이션 (TASK_019 패턴)
- 신규 컬럼 4종 (idempotent ALTER TABLE):
  - `summary_oneliner TEXT DEFAULT ''`
  - `summary_3line TEXT DEFAULT ''`
  - `key_quotes TEXT DEFAULT '[]'`
  - `summarized_at TEXT DEFAULT ''`

### 3. CLI 진입점
```bash
# 5월 호 발행 사이클 시점 일괄 처리
python pipeline/auto_summarizer.py --article-id monthly_digest_2026-04-W3 --max-count 30

# arXiv 4월 신규 일괄
python pipeline/auto_summarizer.py --since-days 30 --topic arxiv --max-count 50
```

### 4. 비용 가드 (governance.md + audit_budget.py)
- Haiku 4.5: 100건 × 평균 2K tokens × $0.80/M = $0.16/주, 월 ~$0.64
- Sonnet 4.6: 100건 × 평균 10K tokens × $3.00/M = $3.00/주, 월 ~$12
- **Max 구독 경유 시 $0** — 매거진 운영 정책상 우선
- audit_budget.py에 `auto_summarizer_monthly_usd_cap` 환경 변수 추가 (default $0)

### 5. 단위 테스트 `tests/test_auto_summarizer.py`
- `test_oneliner_haiku_returns_50char_max`
- `test_3line_sonnet_format` (정확히 3줄)
- `test_quotes_truncate_200char` (자체 콘텐츠 예외 분기)
- `test_request_id_saved_to_logs` (CLAUDE.md 규칙)
- `test_schema_migration_idempotent`
- `test_batch_summarize_skips_already_done` (summary_oneliner NOT NULL 조건)
- `test_korean_utf8_safe`

## 완료 조건

- [ ] `pipeline/auto_summarizer.py` 모듈 신규
- [ ] source_registry 신규 컬럼 4종 (idempotent migration)
- [ ] CLI 명령 (--article-id / --since-days / --source-id / --levels / --max-count / --dry-run)
- [ ] 단위 테스트 7건 pass
- [ ] ruff clean / mojibake clean
- [ ] request_id 모든 호출 후 logs/auto_summarizer_*.json 저장 (CLAUDE.md 규칙)
- [ ] 인용 한도 200자 자동 검증 + truncate
- [ ] dry-run으로 W3 source 15건 요약 시뮬레이션 확인 (실제 LLM 호출 없이 토큰 추정만)

## 후속

- TASK_059 (monthly_curator)가 본 요약 결과를 입력으로 받아 Opus 4.7 클러스터링 + 매거진 섹션 매핑
- 5월 호 Deep Dive #5·#6·#7 + Insight #9 본문은 본 요약 결과를 brief_generator 입력으로 직접 활용

## 완료 처리

```bash
python codex_workflow.py update TASK_058 implemented
python codex_workflow.py update TASK_058 merged
```
