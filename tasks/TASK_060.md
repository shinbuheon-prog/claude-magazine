# TASK_060 — G2 자동 게이트 (confirmed_ratio < 0.85 → 편집자 알림)

## 메타
- **status**: todo
- **prerequisites**: TASK_005 (fact_checker.py), publish-gate skill (현재 5단계)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화 — 인간 게이트 자동화)

---

## 목적

[docs/agent_architecture.md](../docs/agent_architecture.md) §4 인간 게이트 G2 (검증 결과 검토)를 자동화. 현재는 publish-gate skill의 편집자 수동 검토 의무만 있고 **confirmed_ratio < 0.85 자동 강제·알림 부재**.

외부 컨설팅 보고서 §"인간 게이트 G1~G5" 권장 SLA 2시간 내 검토 자동화.

## 해결하는 운영 상황

- 5월 호 발행 사이클 시점 16 꼭지 × fact_checker 결과 자동 검증
- confirmed_ratio < 0.85 (검증 통과율 85% 미만) 시 즉시 Slack 알림 → 편집자 G2 검토
- critical_issues > 0 시 발행 대기 강제 (publish-gate 4단계 진행 차단)
- 매거진 governance.md §"개인정보 처리 원칙" + Sponsored Content 6 의무 + AI 사용 고지 자동 점검

## 구현 단계

### 1. `pipeline/fact_checker.py` 출력 보강
기존 fact_checker는 verdict 결과만 반환. 추가:
```python
def calculate_summary(verdicts: list[ClaimVerdict]) -> dict:
    """반환: {
        total_claims: int,
        confirmed_count: int,
        confirmed_ratio: float,
        overstated_count: int,
        insufficient_source_count: int,
        needs_correction_count: int,
        critical_issues: list[str],
        recommendation: "proceed" | "revise" | "kill",
    }"""
    # ratio 계산 + recommendation 결정 (< 0.85 → revise, < 0.5 → kill)
    ...
```

### 2. `.claude/skills/publish-gate/SKILL.md` G2 자동 게이트 추가
기존 5단계 사이에 G2 단계 신규 (3단계 source_diversity 직후, 4단계 AI 고지 직전):
```markdown
### 3.5 G2 자동 게이트 (confirmed_ratio 검증)
fact_checker 결과를 자동 평가:
- confirmed_ratio >= 0.85 → 자동 통과
- 0.5 <= confirmed_ratio < 0.85 → 편집자 G2 알림 (Slack + 이메일) + SLA 2시간
- confirmed_ratio < 0.5 → 발행 차단 + 즉시 에스컬레이션 + draft revise 권장

```bash
python pipeline/g2_gate.py --draft {draft_path} --strict
```
- exit code 0: 통과
- exit code 1: G2 검토 대기 (편집자 응답 필요)
- exit code 2: 발행 차단 (재작성 필요)
```

### 3. `pipeline/g2_gate.py` 신규
```python
"""G2 자동 게이트 — fact_checker 결과 자동 평가 + Slack 알림.

사용:
    python pipeline/g2_gate.py --draft drafts/article.md --strict
    python pipeline/g2_gate.py --article-id <id> --json
"""
import argparse
import os
import sys
import json
from pathlib import Path

THRESHOLD_PASS = 0.85
THRESHOLD_REVISE = 0.5

def evaluate(article_id: str, strict: bool = True) -> dict:
    """fact_checker 결과 로드 → confirmed_ratio 계산 → 판정.

    반환: {
        article_id, confirmed_ratio, recommendation, decision, sla_deadline,
        slack_notified: bool, escalation_required: bool
    }
    """
    # 1. logs/factcheck_{article_id}.json 로드 (fact_checker 출력)
    # 2. summary 계산 (또는 calculate_summary 호출)
    # 3. recommendation 판정:
    #    - >= 0.85: decision="pass", sla_deadline=None
    #    - 0.5~0.85: decision="g2_review", sla_deadline=now+2h, slack_notified=True
    #    - < 0.5: decision="block", escalation_required=True, slack_notified=True
    # 4. Slack 알림 발송 (NOTIFY_SLACK_WEBHOOK 환경변수 — 기존 failure_repeat_detector 패턴 차용)
    # 5. 결과 dict 반환
    ...

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--strict", action="store_true", help="G2 review 시 exit 1, block 시 exit 2")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = evaluate(args.article_id, args.strict)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"=== G2 게이트 결과 ===")
        print(f"  Article: {result['article_id']}")
        print(f"  Confirmed ratio: {result['confirmed_ratio']:.2%}")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Decision: {result['decision']}")
        if result.get("sla_deadline"):
            print(f"  G2 SLA: {result['sla_deadline']}")

    if args.strict:
        if result["decision"] == "pass":
            return 0
        elif result["decision"] == "g2_review":
            return 1
        else:
            return 2
    return 0
```

### 4. Slack 알림 페이로드
기존 failure_repeat_detector + governance.md §"개인정보 처리 원칙" 패턴:
```json
{
  "text": "🚨 G2 게이트 검토 요청 — Article {article_id}",
  "blocks": [
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "Confirmed ratio: 0.78 (< 0.85)"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "SLA: 2시간 내 검토 필요"}
    },
    {
      "type": "actions",
      "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "검토하기"}, "url": "..."}
      ]
    }
  ]
}
```

### 5. 단위 테스트 `tests/test_g2_gate.py`
- `test_pass_when_ratio_above_085`
- `test_g2_review_when_ratio_between_05_and_085`
- `test_block_when_ratio_below_05`
- `test_slack_notification_payload_format`
- `test_strict_exit_codes` (0/1/2)
- `test_sla_deadline_2h_from_now`

## 완료 조건

- [ ] `pipeline/fact_checker.py` calculate_summary 함수 추가
- [ ] `pipeline/g2_gate.py` 신규
- [ ] `.claude/skills/publish-gate/SKILL.md` 3.5 단계 추가
- [ ] Slack 알림 발송 (NOTIFY_SLACK_WEBHOOK 미설정 시 silent skip)
- [ ] CLI exit code 0/1/2 정상 동작
- [ ] 단위 테스트 6건 pass
- [ ] ruff clean / mojibake clean

## 후속

- TASK_062 (종합 품질 검수)와 결합 — confirmed_ratio + 13항 검수 통합 판정
- 5월 호 발행 사이클 5/24 (3주차 고도화 종료 시점) 시점에 본 게이트 통과 필수

## 완료 처리

```bash
python codex_workflow.py update TASK_060 implemented
python codex_workflow.py update TASK_060 merged
```
