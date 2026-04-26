# TASK_059 — pipeline/monthly_curator.py L4 (Opus 클러스터링 + 매거진 섹션 매핑)

## 메타
- **status**: todo
- **prerequisites**: TASK_055·056·057·058 (3 ingester + auto_summarizer 모두 완료)
- **예상 소요**: 120~180분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화)

---

## 목적

외부 큐레이션 파이프라인 5계층 중 **L4 월간 클러스터링** 계층 신규.

source_registry에 누적된 외부 source (arXiv·HN·Reddit·Anthropic News·OpenAI Blog 등)를 월 단위로 통합 클러스터링 → 매거진 섹션 매핑 후보 제시 → 편집장이 plan_issue로 채택.

기존 Cowork SNS 디제스트 ([reports/monthly_digest_*.md](../reports/)) SOP와 **완전 호환** — 두 디제스트는 동일 Gate 1 승인 흐름.

[docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §6 권장 형식 채택.

## 해결하는 운영 상황

- 매월 외부 source 200~500건 누적 → 편집장 수동 클러스터링 시 4~8시간 소요
- Opus 4.7 자동 클러스터링 → 5~10 클러스터 + 매거진 섹션 매핑 후보 → 편집장 검토 30분 단축
- 갭 분석 자동 (표준 80p 21꼭지 비교축) → 부족 영역 신규 brief 큐 등록

## 구현 단계

### 1. `pipeline/monthly_curator.py` 신규
```python
"""외부 source 월간 클러스터링 + 매거진 섹션 매핑 (외부 큐레이션 L4 계층).

3 단계 처리:
  1. TF-IDF 1차 클러스터링 (sklearn 또는 자체 구현, LLM 호출 없음)
     → 상위 N=20 토큰 동시출현 → 후보 클러스터 5~10개
  2. Opus 4.7 의미적 그룹핑 (1차 결과 검증·통합·이름 부여)
     → 클러스터별 cluster_id, days_covered, source_ids, proposed_angle, magazine_section_candidate
  3. 갭 분석 (Opus 4.7) — 표준 80p 21꼭지 카테고리 vs 클러스터 비교
     → 부족 카테고리 + 신규 brief 후보 제안

사용:
    from pipeline.monthly_curator import curate_monthly_external

    digest = curate_monthly_external(
        month="2026-04",
        feed_filter=None,  # None = 모든 외부 source
        min_cluster_size=2,
        output_path="reports/monthly_external_digest_2026-04.md",
    )

CLI:
    python pipeline/monthly_curator.py --month 2026-04
    python pipeline/monthly_curator.py --month 2026-04 --feed arxiv,hackernews,reddit
    python pipeline/monthly_curator.py --month 2026-04 --dry-run
"""
import os
import sqlite3
from collections import Counter
from anthropic import Anthropic

ROOT = ...
DB_PATH = ...

PROMPT_OPUS_CLUSTER = """다음은 매거진 외부 source 후보 목록입니다 (TF-IDF 1차 클러스터링 결과).

{tfidf_clusters_json}

위 후보를 매거진 정체성(한국어권 Claude 실무자용 무료 발행)에 맞춰:
1. 의미적으로 유사한 클러스터를 통합 (cluster_id 부여)
2. 각 클러스터의 days_covered + source_ids + proposed_angle 명시
3. 매거진 섹션 후보 (cover/feature/deep_dive/insight/interview/review/sponsored)
4. 5~10개 클러스터로 압축 권장

출력: JSON 형식
{{
  "clusters": [
    {{
      "cluster_id": "claude-mcp-2026q2",
      "days_covered": ["2026-04-15", "2026-04-21"],
      "source_ids": ["..."],
      "proposed_angle": "...",
      "magazine_section_candidate": "deep_dive",
      "target_pages": 4,
      "priority_score": 8.5
    }}
  ]
}}
"""

PROMPT_OPUS_GAP = """다음은 매거진 80p 표준 카테고리와 본 월 클러스터 매핑입니다.

표준:
- Cover Story: 1×14p
- Deep Dive: 6×4p = 24p
- Insight: 4×3p = 12p
- Interview: 3×5p = 15p
- Review: 3×3p = 9p
- Sponsored: 1×7p

본 월 클러스터 매핑 결과:
{clusters_summary}

부족한 카테고리·주제 영역을 분석하고 신규 brief 후보를 제안하라.
출력: docs/backlog.md "SNS 디제스트 갭 분석" 섹션과 같은 형식.
"""

def curate_monthly_external(month, feed_filter=None, min_cluster_size=2, output_path=None):
    """월간 외부 디제스트 자동 생성.

    반환: dict — clusters, gap_analysis, source_count, registered_at
    """
    # 1. source_registry에서 month 범위 source 조회 (auto_summarizer 결과 포함)
    # 2. TF-IDF 1차 클러스터링:
    #    - source_id + summary_oneliner + topics에서 토큰 추출
    #    - Counter로 동시출현 빈도 ≥ 2 토큰 추출 (불용어 제거)
    #    - 후보 클러스터 5~10개 생성
    # 3. Opus 4.7 호출 (PROMPT_OPUS_CLUSTER) → 의미적 그룹핑 + 섹션 매핑
    # 4. Opus 4.7 호출 (PROMPT_OPUS_GAP) → 갭 분석 + 신규 brief 후보
    # 5. Markdown 보고서 생성:
    #    - reports/monthly_external_digest_YYYY-MM.md
    #    - editor_approval YAML (Gate 1 미승인 상태)
    #    - 클러스터 테이블 + 섹션 매핑 후보 + 갭 분석 + AI 사용 고지
    # 6. request_id 모든 호출 후 logs/monthly_curator_{month}.json 저장
    # 7. 결과 dict 반환
    ...
```

### 2. 출력 형식 — 기존 SNS 디제스트와 호환
[reports/monthly_digest_2026-04-W3.md](../reports/monthly_digest_2026-04-W3.md) 형식 차용:
- editor_approval YAML 헤더
- 7일 인벤토리 (외부 source 일별)
- 1. 주제·태그 클러스터링 (cluster_id, days_covered, source_ids 등)
- 2. 매거진 섹션 매핑 후보
- 3. 갭 분석
- 4. Gate 2 사전 체크
- 5. AI 사용 고지

### 3. 비용 가드
- TF-IDF: 자체 구현 (LLM 호출 0)
- Opus 4.7 호출: 입력 ~5K tokens × 2회 = 10K tokens × $5/M = $0.05/회
- 매월 1회 = $0.05/월
- **Max 구독 경유 시 $0**
- audit_budget.py에 `monthly_curator_monthly_usd_cap` 환경 변수 추가 (default $0)

### 4. CLI 진입점
```bash
# 5/03 (금) 외부 디제스트 1회분 생성 (4월 source 전체)
python pipeline/monthly_curator.py --month 2026-04

# 특정 feed만 (5월 호 Deep Dive #5·#7 입력 분리)
python pipeline/monthly_curator.py --month 2026-04 --feed arxiv,anthropic

# Dry-run (LLM 호출 없이 TF-IDF 결과만)
python pipeline/monthly_curator.py --month 2026-04 --dry-run
```

### 5. 단위 테스트 `tests/test_monthly_curator.py`
- `test_tfidf_cluster_min_size` (≥ 2 토큰 동시출현)
- `test_opus_cluster_format` (mock Anthropic API)
- `test_gap_analysis_includes_all_categories`
- `test_korean_utf8_safe`
- `test_output_markdown_matches_sns_digest_format` (기존 monthly_digest_*.md 형식 호환)
- `test_request_id_saved_to_logs`
- `test_dry_run_skips_llm` (Anthropic API 호출 0회)

## 완료 조건

- [ ] `pipeline/monthly_curator.py` 모듈 신규
- [ ] CLI 명령 (--month / --feed / --min-cluster-size / --dry-run / --output)
- [ ] 단위 테스트 7건 pass
- [ ] ruff clean / mojibake clean
- [ ] request_id 모든 호출 후 logs/ 저장 (CLAUDE.md 규칙)
- [ ] 출력 Markdown은 기존 SNS 디제스트 형식과 완전 호환 (편집자가 동일 Gate 1 흐름 사용 가능)
- [ ] dry-run으로 4월 source 전체 클러스터링 시뮬레이션 (LLM 호출 0회, TF-IDF만)

## 후속

- 5월 호 발행 사이클 시점 (5/04~5/17) 본 모듈 실행 → Deep Dive #5·#7 + Insight #9 brief 입력
- 6월 호부터 매월 1회 정기 실행 (cron 또는 GitHub Actions)
- 5/31 발행 후 회고 시점에 Phase 9 정식화 결정 (Codex 위임 vs Claude Code 직접 운영)

## 완료 처리

```bash
python codex_workflow.py update TASK_059 implemented
python codex_workflow.py update TASK_059 merged
```
