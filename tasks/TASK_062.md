# TASK_062 — 종합 품질 검수 자동 호출 (template_quality_review.txt + Opus 4.7)

## 메타
- **status**: todo
- **prerequisites**: prompts/template_quality_review.txt (이미 작성), publish-gate skill (5단계 종합 검수 정의)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 불필요
- **Phase**: 9 (외부 큐레이션 파이프라인 정식화 — publish-gate 자동화)

---

## 목적

publish-gate skill의 **5단계 종합 품질 검수**를 LLM 호출로 자동화. 현재는 SKILL.md에 절차만 기술되어 있고 실제 자동 실행 모듈 부재.

[prompts/template_quality_review.txt](../prompts/template_quality_review.txt) (8 검수 기준 + 매거진 고유 5 = 13항)을 Opus 4.7로 호출 → pass/partial/fail 판정 + 우선순위 fix + 개선 본문 자동 출력.

## 해결하는 운영 상황

- 5월 호 발행 사이클 시점 16 꼭지 × 종합 품질 검수 자동 실행
- 편집자가 13항 수동 검토 시 꼭지당 30~60분 → Opus 4.7 자동 호출 시 5~10분 단축
- 발행 직전 "AI 보조 검수 + 인간 최종 승인" 흐름 정착
- governance.md §"개인정보 처리 원칙" + Sponsored Content 6 의무 + AI 사용 고지 + Korean UTF-8 자동 검증

## 구현 단계

### 1. `pipeline/quality_review.py` 신규
```python
"""종합 품질 검수 자동 호출 (publish-gate skill 5단계).

사용:
    from pipeline.quality_review import review_draft

    result = review_draft(
        draft_path="drafts/2026-05/article_X.md",
        article_id="2026-05-claude-code-multi-agent",
        category="feature",
        is_sponsored=False,
    )

CLI:
    python pipeline/quality_review.py --draft drafts/article.md --json
    python pipeline/quality_review.py --draft drafts/article.md --strict
"""
import argparse
import os
import sys
import json
from pathlib import Path
from anthropic import Anthropic

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "template_quality_review.txt"

def review_draft(draft_path: str, article_id: str, category: str = None, is_sponsored: bool = False) -> dict:
    """반환: {
        article_id,
        verdict: "pass" | "partial" | "fail",
        publishable: bool,
        criteria_scores: List[{id, criterion, score, comment, fix_suggestion}],
        priority_fixes: List[{location, problem, recommended_fix}],
        improved_body: str,
        decision: "publish" | "manual_review" | "rewrite",
        request_id: str,
        total_tokens: int,
    }"""
    # 1. draft 본문 로드
    # 2. PROMPT_PATH 로드 + {{article_draft_markdown}} 치환
    # 3. Anthropic Opus 4.7 호출 (effort: high)
    # 4. response 파싱:
    #    - 13 기준 점수 추출
    #    - 우선순위 fix 항목 추출
    #    - 개선된 본문 추출
    # 5. 판정 로직:
    #    - 13/13 통과 → "pass" + publishable=True + decision="publish"
    #    - 10~12 통과 → "partial" + publishable=False + decision="manual_review"
    #    - <= 9 또는 매거진 고유 5건 중 1건이라도 fail → "fail" + decision="rewrite"
    # 6. request_id → logs/quality_review_{article_id}.json 저장 (CLAUDE.md 규칙)
    # 7. 결과 dict 반환
    ...

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--article-id", required=True)
    parser.add_argument("--category", help="feature/deep_dive/insight/interview/review/sponsored")
    parser.add_argument("--sponsored", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="fail 시 exit 1")
    args = parser.parse_args(argv)

    result = review_draft(args.draft, args.article_id, args.category, args.sponsored)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"=== 종합 품질 검수 ===")
        print(f"  Article: {result['article_id']}")
        print(f"  Verdict: {result['verdict']}")
        print(f"  Publishable: {result['publishable']}")
        print(f"  Decision: {result['decision']}")
        if result["priority_fixes"]:
            print(f"\n우선순위 fix {len(result['priority_fixes'])}건:")
            for fix in result["priority_fixes"]:
                print(f"  - {fix['location']}: {fix['problem']}")

    if args.strict and result["verdict"] == "fail":
        return 1
    return 0
```

### 2. `.claude/skills/publish-gate/SKILL.md` 5단계 자동화 명시
기존 5단계 본문에 자동 호출 명령 추가:
```markdown
### 5. 종합 품질 검수 (자동화)
```bash
python pipeline/quality_review.py --draft {draft_path} --article-id {article_id} --strict --json > logs/quality_review_{article_id}.json
```
- pass → 자동 통과 (다음 6단계 진행)
- partial → 편집자 수동 검토 필요 (uncommitted state, 1~3건 fix 후 재실행)
- fail → 발행 차단 + draft 재작성 권장 (다음 단계 진행 금지)
```

### 3. 출력 JSON 형식 (logs/ 저장)
```json
{
  "article_id": "2026-05-claude-code-multi-agent",
  "draft_path": "drafts/2026-05/article_claude-code-multi-agent.md",
  "verdict": "partial",
  "publishable": false,
  "criteria_scores": [
    {"id": 1, "criterion": "단순 뉴스 요약 회피", "score": 4, "comment": "...", "fix_suggestion": null},
    {"id": 2, "criterion": "비즈니스 인사이트 충분성", "score": 3, "comment": "...", "fix_suggestion": "..."},
    ...
    {"id": 13, "criterion": "Korean UTF-8 mojibake 없음", "score": 5, "comment": "CLEAN", "fix_suggestion": null}
  ],
  "priority_fixes": [
    {"location": "§3 두 번째 문단", "problem": "수치 출처 누락 (source_id 미연결)", "recommended_fix": "..."},
    ...
  ],
  "improved_body": "...",
  "decision": "manual_review",
  "request_id": "req_abc123",
  "total_tokens": 24500,
  "timestamp": "2026-05-24T10:30:00+09:00"
}
```

### 4. 비용 가드
- Opus 4.7: 입력 ~10K tokens × $5/M + 출력 ~5K tokens × $25/M = $0.175/회
- 16 꼭지 = $2.80/월
- **Max 구독 경유 시 $0**
- audit_budget.py에 `quality_review_monthly_usd_cap` 환경 변수 추가 (default $0)

### 5. Sponsored 코너 특수 처리
`is_sponsored=True` 시 추가 검수:
- AD 배지 명시 검증
- footer "본 코너는 발행사..." 1줄 검증
- 광고 비율 ≤ 10% 검증 (governance.md §"Sponsored Content" 6 의무)

### 6. 단위 테스트 `tests/test_quality_review.py`
- `test_pass_all_13_criteria`
- `test_partial_with_3_fixes`
- `test_fail_below_9_criteria`
- `test_sponsored_extra_checks`
- `test_request_id_saved`
- `test_strict_exit_codes`
- `test_korean_utf8_safe`
- `test_dry_run_skips_llm` (mock Anthropic API)

## 완료 조건

- [ ] `pipeline/quality_review.py` 모듈 신규
- [ ] `.claude/skills/publish-gate/SKILL.md` 5단계 자동 호출 명령 추가
- [ ] CLI 명령 (--draft / --article-id / --category / --sponsored / --strict / --json)
- [ ] 단위 테스트 8건 pass
- [ ] ruff clean / mojibake clean
- [ ] request_id 모든 호출 후 logs/ 저장
- [ ] Sponsored 코너 추가 검수 정상 동작

## 후속

- TASK_060 (G2 게이트) + TASK_062 (종합 검수) 통합 — publish-gate skill 4단계 (AI 고지) 직전 자동 실행
- 5월 호 발행 사이클 5/28 (4주차 발행 직전) 본 검수 통과 필수

## 완료 처리

```bash
python codex_workflow.py update TASK_062 implemented
python codex_workflow.py update TASK_062 merged
```
