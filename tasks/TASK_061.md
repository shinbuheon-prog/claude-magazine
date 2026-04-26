# TASK_061 — G5 비용 초과 게이트 (자동 차단 → 편집자 승인 흐름)

## 메타
- **status**: todo
- **prerequisites**: TASK_044 (Prompt Caching), audit_budget.py (Round 3)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화 — 인간 게이트 자동화)

---

## 목적

[docs/agent_architecture.md](../docs/agent_architecture.md) §4 인간 게이트 G5 (비용 초과 승인)를 자동화. 현재 audit_budget.py는 illustration cap 자동 차단만 (편집자 승인 흐름 부재).

외부 컨설팅 보고서 §"인간 게이트 G5" 권장 SLA 30분 내 승인 + 옵션 (계속 / 중단 / 모델 다운그레이드).

## 해결하는 운영 상황

- 5월 호 발행 사이클 시점 외부 API (arXiv·Reddit·OpenAI 호출) 또는 LLM (Sonnet·Opus) 비용 가드 적용
- 단일 기사 비용 > 예산의 150% 시 자동 차단 + Slack 알림
- 편집자 30분 내 응답 (계속 진행 / 중단 / 모델 다운그레이드 — Opus → Sonnet)
- 매거진 메모리 정합 — Max 구독 경유 시 LLM 비용 $0이라 본 게이트는 **외부 API 도입 시점부터 활성화** (5/05~ 외부 ingester 머지 후)

## 구현 단계

### 1. `scripts/audit_budget.py` 보강 — 기사별 비용 추적
기존: illustration 월간 cap만 (계층 3)
추가: 기사별 비용 (계층 2) + 에이전트별 비용 (계층 1)

```python
"""기사별 비용 추적 (계층 2):
data/cost_tracking/article_{article_id}_costs.json
{
  "article_id": "...",
  "estimated_budget_usd": 1.0,
  "actual_costs": {
    "scout": {"tokens_input": 1000, "tokens_output": 200, "cost_usd": 0.003},
    "architect": {"tokens_input": 5000, "tokens_output": 1500, "cost_usd": 0.038},
    "drafter": {"tokens_input": 8000, "tokens_output": 5000, "cost_usd": 0.099},
    "verifier": {"tokens_input": 12000, "tokens_output": 2000, "cost_usd": 0.110},
    "external_apis": {"arxiv": 0.0, "reddit": 0.0}
  },
  "total_cost_usd": 0.250,
  "budget_utilization_pct": 25.0,
  "g5_triggered": false,
  "editor_decision": null  // "continue" | "abort" | "downgrade_to_haiku"
}
"""

def check_article_budget(article_id: str, threshold_pct: float = 150.0) -> dict:
    """기사 누적 비용이 예산의 threshold% 초과 시 G5 트리거.

    반환: {article_id, current_cost_usd, budget_usd, utilization_pct,
            g5_triggered: bool, action_required: str | None}
    """
    ...
```

### 2. `pipeline/g5_gate.py` 신규
```python
"""G5 비용 초과 게이트.

사용:
    python pipeline/g5_gate.py --article-id <id> --check
    python pipeline/g5_gate.py --article-id <id> --decide continue|abort|downgrade
"""
import argparse
import os
import sys
import json

THRESHOLD_PCT = 150.0  # 예산의 150% 초과 시 차단
SLA_MINUTES = 30

def check_and_notify(article_id: str) -> dict:
    """
    1. audit_budget.check_article_budget(article_id) 호출
    2. utilization_pct >= 150% 시:
        - 자동 차단 (다음 에이전트 실행 금지)
        - Slack 알림 + SLA 30분
        - 편집자 결정 대기 (data/cost_tracking/g5_pending_{article_id}.json 생성)
    3. 결과 반환
    """
    ...

def apply_decision(article_id: str, decision: str) -> dict:
    """편집자 결정 적용:
    - "continue": 차단 해제 + 비용 cap 200%로 일시 상향
    - "abort": draft 폐기 + status="killed" 처리
    - "downgrade_to_haiku": 후속 에이전트 모델을 Haiku 4.5로 강제 변경
    """
    ...
```

### 3. Slack 알림 페이로드
```json
{
  "text": "💰 G5 비용 초과 — Article {article_id}",
  "blocks": [
    {"type": "section", "text": {"type": "mrkdwn", "text": "현재 비용: $1.50 (예산 $1.00의 150%)"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "SLA: 30분 내 결정 필요"}},
    {
      "type": "actions",
      "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "계속 진행"}, "value": "continue"},
        {"type": "button", "text": {"type": "plain_text", "text": "중단"}, "value": "abort"},
        {"type": "button", "text": {"type": "plain_text", "text": "Haiku 다운그레이드"}, "value": "downgrade"}
      ]
    }
  ]
}
```

### 4. CLI 통합
```bash
# 자동 점검 (각 에이전트 실행 직후 호출)
python pipeline/g5_gate.py --article-id 2026-05-claude-code-multi-agent --check

# 편집자 결정 적용
python pipeline/g5_gate.py --article-id 2026-05-claude-code-multi-agent --decide downgrade
```

### 5. 단위 테스트 `tests/test_g5_gate.py`
- `test_check_below_threshold_no_trigger`
- `test_check_above_threshold_triggers_g5`
- `test_apply_continue_unblocks_pipeline`
- `test_apply_abort_marks_killed`
- `test_apply_downgrade_changes_model_to_haiku`
- `test_slack_notification_payload`
- `test_sla_deadline_30_minutes`

### 6. 환경변수
```bash
# .env 추가
ARTICLE_BUDGET_DEFAULT_USD=1.0  # 기사당 기본 예산
G5_THRESHOLD_PCT=150.0  # 트리거 임계값
G5_SLA_MINUTES=30  # 편집자 응답 SLA
NOTIFY_SLACK_WEBHOOK=...  # 기존 사용 중
```

## 완료 조건

- [ ] `scripts/audit_budget.py` check_article_budget 함수 추가
- [ ] `pipeline/g5_gate.py` 신규
- [ ] data/cost_tracking/ 디렉토리 + JSON 형식 명세
- [ ] Slack 알림 (3 액션 버튼)
- [ ] CLI 명령 (--check / --decide)
- [ ] 단위 테스트 7건 pass
- [ ] ruff clean / mojibake clean
- [ ] Max 구독 경유 시 비용 $0 — 본 게이트는 외부 API 도입 시점부터 활성화 (5/05~)

## 후속

- TASK_063 (source_diversity 강제) 후속 — 외부 API 호출 비용도 본 게이트 적용
- 5월 호 발행 사이클 5/05 (외부 ingester 머지 직후) 본 게이트 활성화

## 완료 처리

```bash
python codex_workflow.py update TASK_061 implemented
python codex_workflow.py update TASK_061 merged
```
