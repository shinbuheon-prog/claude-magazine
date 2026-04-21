# TASK_004 — 출처 레지스트리 (SQLite)

## 메타
- **status**: todo
- **prerequisites**: TASK_001
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요

---

## 목적
모든 소스를 추적 가능한 형태로 저장하는 SQLite 기반 레지스트리를 구현한다.
저작권 통제·정정 프로토콜·출처 감사의 핵심 자산.

---

## 구현 명세

### 파일: `pipeline/source_registry.py` (기존 파일 검토 후 완성)

### DB 경로
```python
DB_PATH = Path(os.environ.get("SOURCE_DB_PATH", "data/source_registry.db"))
```

### 스키마
```sql
CREATE TABLE IF NOT EXISTS sources (
    source_id        TEXT PRIMARY KEY,   -- "src-" + uuid4 앞 8자
    url              TEXT NOT NULL,
    publisher        TEXT DEFAULT '',
    retrieved_at     TEXT,               -- ISO 8601 UTC
    version_hash     TEXT DEFAULT '',    -- SHA256[:8] of content_preview
    rights_status    TEXT DEFAULT 'unknown',  -- free|restricted|paid|unknown
    claim_ids        TEXT DEFAULT '[]',  -- JSON 배열
    quote_limit      INTEGER DEFAULT 200,
    used_in_channels TEXT DEFAULT '[]',  -- JSON 배열: ["web","email","sns"]
    article_id       TEXT DEFAULT ''
);
```

### 필수 함수 시그니처
```python
def add_source(url, publisher="", content_preview="",
               rights_status="unknown", quote_limit=200, article_id="") -> str:
    """이미 등록된 URL이면 기존 source_id 반환"""

def get_source(source_id: str) -> dict | None:
    """claim_ids, used_in_channels는 JSON 파싱해서 list로 반환"""

def mark_used(source_id: str, channel: str) -> None:
    """중복 없이 channel 추가"""

def list_sources(article_id: str) -> list[dict]:
    """기사 ID로 소스 목록 반환"""
```

### 스모크 테스트 (`if __name__ == "__main__":` 블록)
```python
sid = add_source(url="https://example.com", publisher="Test", article_id="art-001")
assert sid.startswith("src-")
assert get_source(sid)["url"] == "https://example.com"
mark_used(sid, "web")
mark_used(sid, "web")  # 중복 추가 → 한 번만 저장되어야 함
assert get_source(sid)["used_in_channels"] == ["web"]
assert len(list_sources("art-001")) == 1
print("✓ source_registry 스모크 테스트 통과")
```

---

## 완료 조건
- [ ] `python pipeline/source_registry.py` 실행 시 "✓ 스모크 테스트 통과" 출력
- [ ] `data/source_registry.db` 파일 생성 확인
- [ ] 중복 URL 등록 시 기존 source_id 반환 확인
- [ ] used_in_channels 중복 방지 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_004 implemented
```
