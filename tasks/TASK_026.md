# TASK_026 — 편집자 판정 누적 시스템 (Expertise Diffusion)

## 메타
- **status**: todo
- **prerequisites**: 없음
- **예상 소요**: 75분
- **서브에이전트 분할**: 가능 (A: DB·수집 로직 / B: 프롬프트 주입)
- **Phase**: 4 (전문 지식 인프라화)

---

## 목적
Miessler "Expertise Diffusion into Public Knowledge" 원칙 적용.
편집자가 기사를 수정한 **판정 내역을 영구 자산화**해, 다음 기사 생성 시 Claude에 자동 주입.
매호 발행할 때마다 매거진이 **지수적으로 똑똑해지는 복리 효과**.

리포트 인용: _"전문가 두뇌 → AI 스킬·SOP·컨텍스트 파일 → 절대 사라지지 않음 → 모든 AI 인스턴스가 동시에 더 똑똑해짐."_

---

## 구현 명세

### 1. 생성 파일
```
pipeline/
├── editor_corrections.py        ← 판정 수집·조회·요약
└── heuristics_injector.py       ← 프롬프트에 과거 판정 주입

data/
└── editor_corrections.db        ← SQLite (gitignore)

prompts/
└── editor_heuristics.md         ← 주간 자동 요약 (gitcommit됨)

scripts/
└── collect_corrections.py       ← git diff 기반 수동 수집
```

### 2. SQLite 스키마

```sql
CREATE TABLE corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    article_id TEXT,
    category TEXT,               -- 'interview' | 'deep_dive' | ...
    correction_type TEXT NOT NULL,
    -- 'exaggeration' | 'tone' | 'factual' | 'source' | 'structure' | 'style' | 'clarity'
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    editor_note TEXT,            -- 편집자 의도 (왜 고쳤는지)
    severity TEXT DEFAULT 'medium',  -- 'low' | 'medium' | 'high'
    tags TEXT,                   -- 쉼표구분: 'numeric,overstatement'
    source_commit TEXT           -- 수집된 git commit hash
);

CREATE INDEX idx_correction_type ON corrections(correction_type);
CREATE INDEX idx_category ON corrections(category);
CREATE INDEX idx_timestamp ON corrections(timestamp);
```

### 3. `pipeline/editor_corrections.py` 시그니처

```python
def record_correction(
    article_id: str,
    category: str,
    correction_type: str,
    original: str,
    corrected: str,
    editor_note: str | None = None,
    severity: str = "medium",
    tags: list[str] | None = None,
) -> int:
    """SQLite에 판정 추가. 반환: correction id"""

def query_corrections(
    category: str | None = None,
    correction_type: str | None = None,
    since_days: int = 90,
    limit: int = 50,
) -> list[dict]:
    """필터링된 판정 조회 (최근순)"""

def summarize_for_prompt(
    category: str,
    max_examples: int = 10,
) -> str:
    """
    Claude에 주입할 마크다운 문자열 생성.
    카테고리별 최근 판정에서 severity 높은 순 max_examples개 추출.
    반환 예시:
    ---
    ## 편집자 판정 사례 (최근 30건 중 5건 요약)

    1. [과장 수정] "최초로" → "주요 중 하나"
       이유: 원문은 "업계 선두 중 하나"로 기술됨
    2. [수치 정정] "30% 증가" → "약 27%"
       이유: 원문 수치 28.7%를 반올림 일관성 위해 수정
    ...
    ---
    이 사례들을 참고해 동일 패턴을 피하세요.
    """
```

### 4. `scripts/collect_corrections.py` — git diff 기반 수집

```bash
# 최근 commit에서 drafts/ 수정 추적
python scripts/collect_corrections.py \
    --since HEAD~5 --until HEAD \
    --interactive  # 각 수정에 대해 type·severity 입력
```

동작:
1. `git diff --unified=0` 로 변경 hunk 추출
2. 각 hunk에 대해 편집자에게 질문 (interactive mode):
   - "이 수정의 type은? (exaggeration/tone/factual/source/structure/style/clarity)"
   - "severity? (low/medium/high)"
   - "editor_note? (선택)"
3. SQLite에 저장

비대화 모드(`--auto`): Haiku로 자동 분류 (best-effort).

### 5. `pipeline/heuristics_injector.py` — 프롬프트 주입

기존 `brief_generator.py`, `draft_writer.py`, `fact_checker.py` 호출 직전 훅:

```python
from pipeline.heuristics_injector import inject_heuristics

def generate_brief(topic, category, ...):
    heuristics_block = inject_heuristics(category)

    system_prompt = (
        BASE_SYSTEM_PROMPT +
        "\n\n" + heuristics_block  # ← 과거 편집자 판정 주입
    )
    # ...
```

Cache-aware: `inject_heuristics()`는 쿼리 결과를 해시로 캐싱해 동일 category는 동일 prompt 생성 (Anthropic cache hit 극대화).

### 6. 주간 자동 요약 → `prompts/editor_heuristics.md`

```bash
# 매주 일요일 Cron (n8n workflow_5_weekly_summary.json)
python -c "
from pipeline.editor_corrections import summarize_for_prompt
import pathlib
summary = summarize_for_prompt(category='all', max_examples=30)
pathlib.Path('prompts/editor_heuristics.md').write_text(summary)
"
```

이 파일은 **git에 커밋**되어 매거진의 누적 지혜가 버전 관리됨.

### 7. CLI

```bash
# 판정 수동 추가
python pipeline/editor_corrections.py add \
    --article-id art-001 --category deep_dive \
    --type exaggeration --original "최초로" --corrected "주요 중 하나" \
    --severity high --note "업계 선두 중 하나로 기술됨"

# 카테고리별 최근 판정 조회
python pipeline/editor_corrections.py list --category deep_dive --since-days 30

# 프롬프트 블록 미리보기
python pipeline/heuristics_injector.py preview --category interview
```

---

## 완료 조건
- [ ] `pipeline/editor_corrections.py` 생성 (record·query·summarize)
- [ ] SQLite 스키마 + idempotent init
- [ ] `pipeline/heuristics_injector.py` 생성 + cache-aware 해시
- [ ] `scripts/collect_corrections.py` (interactive + `--auto` Haiku 분류)
- [ ] `brief_generator.py`, `draft_writer.py`, `fact_checker.py`에 `inject_heuristics` 호출 추가
- [ ] `.gitignore`에 `data/editor_corrections.db` 추가
- [ ] `prompts/editor_heuristics.md` 초기 생성 (빈 파일)
- [ ] 스모크 테스트: 가짜 judgment 3건 추가 → `summarize_for_prompt()` 마크다운 반환 확인
- [ ] 기존 파이프라인 하위 호환 (heuristics 없을 때 skip)

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_026 implemented
```

## 주의사항
- DB 파일은 절대 커밋 금지 (PII·편집 의도 내부 데이터)
- heuristics 주입으로 system prompt 길이 증가 → Anthropic cache 활용 필수
- 판정 severity 'high' 15건 이상 시 Slack 알림 (quality drift 감지)
- `editor_heuristics.md`는 ≤2000 단어 유지 (토큰 비용)
