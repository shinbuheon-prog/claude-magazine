# TASK_027 — 자율 개선 루프 (Autonomous Optimization)

## 메타
- **status**: todo
- **prerequisites**: TASK_025, TASK_026
- **예상 소요**: 90분
- **서브에이전트 분할**: 가능 (A: 실패 수집기 / B: SOP 업데이트 제안기)
- **Phase**: 4 (자율 개선)

---

## 목적
Miessler "Autonomous Component Optimization" 사이클 구현.

> 목표 정의 → 에이전트 실행 → 광범위한 로깅 → 실패 수집 → 자율 개선 → SOP 업데이트 → 반복

**현재 부족**: 로깅·관측은 있지만 **실패가 프롬프트·기준으로 자동 반영되지 않음**. 매주 편집자가 수동 반영.
**목표**: 주간 자동 분석 → 프롬프트·이상 상태 기준 업데이트 **제안서 생성** (적용은 사람이 승인).

---

## 구현 명세

### 1. 생성 파일
```
pipeline/
├── failure_collector.py         ← logs/ · editorial_lint 실패 · editor_corrections 통합
└── sop_updater.py               ← Opus로 패턴 분석 + 업데이트 제안

scripts/
└── weekly_improvement.py        ← 전체 루프 진입점 (Cron 대상)

reports/
└── improvement_YYYY-MM-DD.md    ← 주간 개선 제안 보고서 (gitcommit됨)

n8n/
└── workflow_5_weekly_improvement.json   ← 매주 일 23:00 KST
```

### 2. `pipeline/failure_collector.py` — 실패 통합 수집

```python
def collect_failures(since_days: int = 7) -> dict:
    """
    반환: {
        "period": {"from": ISO, "to": ISO},
        "editorial_lint_failures": [  # editorial_lint.py 실패 기록
            {"check_id", "count", "examples": [...]},
        ],
        "standards_failures": [  # TASK_025 기준 실패
            {"rule_id", "category", "count", "examples": [...]},
        ],
        "editor_corrections": [  # TASK_026 DB에서
            {"type", "count", "severity_high_count"},
        ],
        "langfuse_anomalies": [  # 비정상 패턴 (있으면)
            {"metric", "baseline", "current", "delta_pct"},
        ],
        "total_articles": int,
    }
    """
```

데이터 소스:
- `logs/factcheck_*.json`, `logs/brief_*.json` (editorial_lint 실패는 JSON에 기록 가정)
- `data/editor_corrections.db` (TASK_026)
- Langfuse API (LANGFUSE_ENABLED=True일 때만)
- Ghost Content API (발행 완료 기사 목록)

### 3. `pipeline/sop_updater.py` — Opus 분석 + 제안

```python
def analyze_and_propose(failures: dict) -> dict:
    """
    Opus 4.7 호출로 패턴 분석 → 업데이트 제안 생성.
    반환: {
        "patterns": [  # 반복 실패 패턴
            {"pattern": "과장된 수치 표현", "frequency": 12, "affected_categories": [...]},
        ],
        "proposed_updates": [
            {
                "target_file": "prompts/template_B_draft.txt",
                "diff": "--- 기존\n+++ 제안\n...",
                "rationale": "최근 4주간 '최초로' 수정 8건",
                "expected_impact": "draft 과장 표현 50% 감소 예상"
            },
            {
                "target_file": "spec/article_standards.yml",
                "diff": "...",
                "rationale": "...",
            },
        ],
        "opus_request_id": str,
        "confidence": float,  # 0~1
    }
    """
```

**보수적 원칙**: Opus는 **제안만**. 실제 파일 수정은 사람이 diff 리뷰 후 수동 적용.

### 4. `scripts/weekly_improvement.py` — 진입점

```bash
python scripts/weekly_improvement.py
# 또는
python scripts/weekly_improvement.py --since-days 14 --output reports/custom.md
```

동작:
1. `collect_failures(since_days=7)` 호출
2. `analyze_and_propose(failures)` 호출
3. 결과를 `reports/improvement_YYYY-MM-DD.md`로 저장
4. Slack 알림: "주간 개선 제안 N건 대기 중 → {report_url}"

### 5. 보고서 형식 (`reports/improvement_*.md`)

```markdown
# 주간 개선 제안 — 2026-05-01 ~ 2026-05-07

## 요약
- 발행 기사: 3건
- editorial_lint 실패: 11건 (주요: quote-fidelity 5건, ai-disclosure 3건)
- 편집자 판정: 23건 (과장 8건, 수치 5건, 톤 4건, 기타 6건)
- 비정상 메트릭: 팩트체크 평균 시간 +35% (6.2s → 8.4s)

## 반복 패턴 3건 발견

### 1. 과장 표현 패턴 (빈도 12, severity high 4)
- 대표 사례: "최초로" (4회), "최대의" (3회), "혁명적인" (5회)
- 영향 카테고리: deep_dive, feature

### 2. ...

## 제안된 업데이트

### [HIGH] prompts/template_B_draft.txt
기대 효과: draft 과장 표현 50% 감소
근거: 최근 4주간 '최초로' 수정 8건

\`\`\`diff
--- a/prompts/template_B_draft.txt
+++ b/prompts/template_B_draft.txt
@@ -15,3 +15,8 @@
 ## 스타일 규칙
 - 군더더기 금지
+- 과장 표현 금지: "최초로", "최대의", "혁명적인" 등
+  대신 "주요 중 하나", "업계 선두급", "주목할 만한" 사용
+- 수치 표현은 반드시 반올림 기준 명시 (소수점 1자리)
\`\`\`

### [MEDIUM] spec/article_standards.yml
...

## 사람 승인 필요
위 제안 diff를 검토 후 적용:
1. git checkout -b improvement-2026-05-07
2. 제안된 파일 수정 (diff 참고)
3. git commit -m "chore: 주간 개선 적용"
4. PR 생성
```

### 6. n8n workflow_5_weekly_improvement.json

- Cron: 매주 일요일 23:00 KST
- Execute Command: `python scripts/weekly_improvement.py`
- Slack Notify: 제안 N건 알림 + report 링크
- GitHub Issue 자동 생성 옵션 (`--create-issue`): 제안서를 issue 본문으로

### 7. Opus 호출 비용 관리
- 주간 1회 Opus 호출 (월 4회)
- 입력: 7일치 실패 요약 (≤ 30K tokens)
- 출력: 제안서 (≤ 5K tokens)
- 예상 비용: ≈$0.5/주 (월 $2)

---

## 완료 조건
- [ ] `pipeline/failure_collector.py` 구현
- [ ] `pipeline/sop_updater.py` Opus 호출 + 제안 파싱
- [ ] `scripts/weekly_improvement.py` 진입점
- [ ] `reports/` 디렉토리 생성 + `.gitignore` 제외 (gitcommit됨 — 버전관리)
- [ ] `n8n/workflow_5_weekly_improvement.json` 생성
- [ ] Opus 호출 실패 시 graceful fallback (빈 report + 에러 로그)
- [ ] 스모크 테스트: 7일치 가짜 실패 데이터 → report 생성 → 마크다운 포맷 유효
- [ ] 실제 파일 자동 수정 안 함 (제안만)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_027 implemented
```

## 주의사항
- **Opus는 제안만, 실제 수정은 사람** — 자동 머지 절대 금지
- 제안서에 `git diff` 형식 포함 (편집자가 `git apply` 가능)
- 민감 정보(API 키·내부 데이터) report에 포함 금지 — PII 스크러빙
- Langfuse 없으면 그 섹션만 skip, 전체 실패 금지
- 제안서 버전 관리로 과거 제안 추적 가능
