# TASK_008 — Langfuse 관측 연동

## 메타
- **status**: todo
- **prerequisites**: TASK_003 (TASK_001~007과 병렬 진행 가능)
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요

---

## 목적
모든 Claude API 호출을 Langfuse로 추적해 토큰 비용·프롬프트 버전·품질 평가를 관리한다.

---

## 구현 명세

### 생성할 파일: `pipeline/observability.py`
```python
"""
Langfuse 래퍼 — 모든 pipeline/ 모듈에서 import해서 사용
"""
import os
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

try:
    from langfuse import Langfuse
    _lf = Langfuse(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
        host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
    LANGFUSE_ENABLED = bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))
except ImportError:
    LANGFUSE_ENABLED = False
    _lf = None

def trace_llm_call(name: str, model: str, topic: str = "", article_id: str = ""):
    """
    데코레이터: Claude API 호출 함수를 Langfuse trace로 감싼다.
    Langfuse 미설정 시 투명하게 통과 (예외 없음).
    사용:
        @trace_llm_call(name="brief_generation", model="claude-sonnet-4-6", topic=topic)
        def _call():
            ...
    """
    # 구현

def log_usage(trace_id: str, input_tokens: int, output_tokens: int, model: str) -> None:
    """토큰 사용량을 Langfuse trace에 기록"""
    # 구현
```

### pipeline/ 각 모듈에 추가할 패턴
```python
# brief_generator.py, draft_writer.py, fact_checker.py, channel_rewriter.py 모두 동일 패턴

from pipeline.observability import trace_llm_call, log_usage, LANGFUSE_ENABLED

# Claude API 호출 전후
if LANGFUSE_ENABLED:
    trace = _lf.trace(name="brief_generation", metadata={"topic": topic, "model": model})
# ... API 호출 ...
if LANGFUSE_ENABLED:
    log_usage(trace.id, final.usage.input_tokens, final.usage.output_tokens, model)
```

### 추적 항목 (trace metadata)
| 필드 | 값 |
|---|---|
| name | brief_generation / draft_writing / fact_checking / channel_rewriting |
| model | 사용 모델명 |
| topic | 기사 주제 |
| article_id | 기사 ID (있으면) |
| input_tokens | API 응답의 usage.input_tokens |
| output_tokens | API 응답의 usage.output_tokens |

---

## 완료 조건
- [ ] `pipeline/observability.py` 생성
- [ ] Langfuse 미설정 시 모든 pipeline 모듈이 정상 동작 (LANGFUSE_ENABLED=False 경로)
- [ ] `.env`에 Langfuse 키 입력 후 `brief_generator.py` 실행 → Langfuse 대시보드에서 trace 확인
- [ ] `pipeline/` 4개 모듈에 observability 패턴 추가

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_008 implemented
```
