# TASK_003 — Claude API 브리프·초안 파이프라인

## 메타
- **status**: todo
- **prerequisites**: TASK_001
- **예상 소요**: 45분
- **서브에이전트 분할**: 가능 (brief_generator / draft_writer 각각 독립 구현)

---

## 목적
소스 묶음 → 기사 브리프 JSON → 섹션 초안 텍스트 흐름을 완성한다.

---

## 서브에이전트 A: `pipeline/brief_generator.py`

### 함수 시그니처
```python
def generate_brief(topic: str, source_bundle: str) -> dict:
    """
    입력: topic(주제), source_bundle(소스 텍스트 묶음)
    출력: 아래 JSON 스키마를 만족하는 dict
    모델: claude-sonnet-4-6
    프롬프트: prompts/template_A_brief.txt 로드
    스트리밍: 필수
    로그: logs/brief_YYYYMMDD_HHMMSS.json (request_id 포함)
    """
```

### 출력 JSON 스키마 (반드시 준수)
```json
{
  "working_title": "string",
  "angle": "string",
  "why_now": "string",
  "outline": [{"section": "string", "points": ["string"]}],
  "evidence_map": [{"claim": "string", "source_id": "string"}],
  "unknowns": ["string"],
  "risk_flags": ["string"]
}
```

### CLI 인터페이스
```bash
python pipeline/brief_generator.py --topic "TOPIC" [--sources file1.md file2.md] [--out brief.json]
```

### 스모크 테스트
```bash
python pipeline/brief_generator.py --topic "Claude Sonnet 4.6 업데이트 분석"
# 기대: 위 JSON 스키마를 만족하는 출력, logs/ 에 로그 파일 생성
```

---

## 서브에이전트 B: `pipeline/draft_writer.py`

### 함수 시그니처
```python
def write_section(brief: dict, section_name: str, source_bundle: str = "") -> str:
    """
    입력: brief(브리프 dict), section_name(섹션 제목), source_bundle
    출력: 마크다운 텍스트 (각 주장 끝에 (source_id) 표기)
    모델: claude-sonnet-4-6
    프롬프트: prompts/template_B_draft.txt 로드
    스트리밍: 필수 (실시간 출력)
    로그: logs/draft_YYYYMMDD_HHMMSS.json
    """
```

### CLI 인터페이스
```bash
python pipeline/draft_writer.py --brief brief.json --section "섹션명" [--out draft.md]
```

### 스모크 테스트
```bash
# brief.json이 있어야 함 (서브에이전트 A 먼저 실행)
python pipeline/draft_writer.py --brief /tmp/test_brief.json --section "서론"
# 기대: 마크다운 텍스트 출력, (source_id) 표기 포함
```

---

## 완료 조건
- [ ] `brief_generator.py` 스모크 테스트 통과 (JSON 스키마 완전 준수)
- [ ] `draft_writer.py` 스모크 테스트 통과 (source_id 표기 포함)
- [ ] 두 모듈 모두 `logs/` 에 request_id 저장 확인
- [ ] `from pipeline.brief_generator import generate_brief` import 오류 없음

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_003 implemented
```
