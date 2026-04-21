# TASK_005 — 팩트체크 에이전트 (Opus 4.7)

## 메타
- **status**: todo
- **prerequisites**: TASK_003, TASK_004
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요

---

## 목적
초안의 각 주장 문장을 출처와 대조해 판정 표를 생성한다.
Opus 4.7 사용 — **월간 딥리서치·최종 검토에만** 호출할 것.

---

## 구현 명세

### 파일: `pipeline/fact_checker.py` (기존 파일 검토 후 완성)

### 함수 시그니처
```python
def run_factcheck(draft_text: str, source_bundle: str) -> str:
    """
    모델: claude-opus-4-7
    프롬프트: prompts/template_C_factcheck.txt 로드
    스트리밍: 필수
    로그: logs/factcheck_YYYYMMDD_HHMMSS.json (request_id 포함)
    반환: 마크다운 표 + 위험도 요약 텍스트
    """

def load_sources_for_article(article_id: str | None) -> str:
    """
    source_registry에서 기사별 소스 묶음 조회.
    TASK_004 미완료 시: "(source_registry 미연동)" 반환 (예외 발생 금지)
    """
```

### CLI 인터페이스
```bash
python pipeline/fact_checker.py --draft drafts/article.md [--article-id art-001] [--out result.md]
```

### 출력 형식 (반드시 이 구조)
```markdown
| 문장 | 판정 | 근거 source_id | 수정 제안 |
|---|---|---|---|
| "..." | 확인됨 | src-001 | - |
| "..." | 과장됨 | src-002 | "약 29%"로 수정 |
| "..." | 출처 불충분 | UNKNOWN | 추가 출처 필요 |
| "..." | 수정 필요 | src-003 | "X" → "Y" |

## 전체 위험도: 낮음 / 중간 / 높음

## 즉시 수정 필요
- ...

## 추가 확인 필요
- ...
```

### 스모크 테스트
```bash
echo "Claude의 MAU는 3,000만 명이다. 시장 점유율은 99%를 기록했다." > /tmp/test_draft.md
python pipeline/fact_checker.py --draft /tmp/test_draft.md
# 기대: 마크다운 표 출력, logs/에 로그 저장
```

---

## 완료 조건
- [ ] 스모크 테스트 통과 (마크다운 표 출력)
- [ ] 4개 판정 모두 출력 가능 확인
- [ ] `logs/` 에 request_id 포함된 로그 저장 확인
- [ ] TASK_004 미연동 상태에서도 예외 없이 동작 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_005 implemented
```
