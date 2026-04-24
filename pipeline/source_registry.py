"""
출처 레지스트리 — SQLite 기반 소스 추적 시스템
사용법: python pipeline/source_registry.py
"""
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("SOURCE_DB_PATH", "data/source_registry.db"))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
DB_PATH.parent.mkdir(exist_ok=True)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    source_id        TEXT PRIMARY KEY,
    url              TEXT NOT NULL,
    publisher        TEXT DEFAULT '',
    retrieved_at     TEXT,
    version_hash     TEXT DEFAULT '',
    rights_status    TEXT DEFAULT 'unknown',
    claim_ids        TEXT DEFAULT '[]',
    quote_limit      INTEGER DEFAULT 200,
    used_in_channels TEXT DEFAULT '[]',
    article_id       TEXT DEFAULT '',
    language         TEXT DEFAULT 'unknown',
    stance           TEXT DEFAULT 'neutral',
    is_official      INTEGER DEFAULT 0
);
"""

# TASK_019: 소스 다양성 규칙 엔진용 확장 컬럼 (idempotent migration)
DIVERSITY_COLUMNS = [
    ("language", "TEXT DEFAULT 'unknown'"),
    ("stance", "TEXT DEFAULT 'neutral'"),
    ("is_official", "INTEGER DEFAULT 0"),
]


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """기존 sources 테이블에 TASK_019 확장 컬럼을 추가 (idempotent)."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
    for col_name, col_def in DIVERSITY_COLUMNS:
        if col_name not in existing_cols:
            conn.execute(f"ALTER TABLE sources ADD COLUMN {col_name} {col_def}")
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    _migrate_schema(conn)
    return conn


def init_db() -> None:
    """외부 호출용 DB 초기화 (스키마 생성 + 마이그레이션)."""
    conn = _get_conn()
    try:
        pass
    finally:
        conn.close()


def _hash_content(content_preview: str) -> str:
    return hashlib.sha256(content_preview.encode("utf-8")).hexdigest()[:8]


def add_source(
    url,
    publisher="",
    content_preview="",
    rights_status="unknown",
    quote_limit=200,
    article_id="",
    language="unknown",
    stance="neutral",
    is_official=0,
    auto_classify_stance: bool = False,
    topic: str = "",
) -> str:
    """이미 등록된 URL이면 기존 source_id를 반환한다.

    auto_classify_stance=True이면 Haiku 4.5를 호출해 stance를 자동 분류한다.
    API 키가 없거나 호출 실패 시 전달된 stance 값 (기본 'neutral')을 그대로 사용한다.
    """
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT source_id FROM sources WHERE url = ?", (url,)).fetchone()
        if existing:
            return existing["source_id"]

        # stance 자동 분류 (실패 시 전달받은 값 유지)
        if auto_classify_stance and content_preview:
            try:
                from pipeline.source_diversity import classify_stance
            except ModuleNotFoundError:
                try:
                    from source_diversity import classify_stance  # type: ignore
                except ModuleNotFoundError:
                    classify_stance = None  # type: ignore
            if classify_stance is not None:
                try:
                    inferred = classify_stance(content_preview, topic)
                    if inferred in {"pro", "neutral", "con", "unknown"}:
                        stance = inferred
                except Exception:
                    # 자동 분류 실패 시 전달받은 stance 유지 (예외 전파 금지)
                    pass

        source_id = f"src-{uuid.uuid4().hex[:8]}"
        retrieved_at = datetime.now(timezone.utc).isoformat()
        version_hash = _hash_content(content_preview) if content_preview else ""

        conn.execute(
            """
            INSERT INTO sources (
                source_id, url, publisher, retrieved_at, version_hash,
                rights_status, quote_limit, article_id,
                language, stance, is_official
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                url,
                publisher,
                retrieved_at,
                version_hash,
                rights_status,
                quote_limit,
                article_id,
                language,
                stance,
                int(bool(is_official)),
            ),
        )
        conn.commit()
        return source_id
    finally:
        conn.close()


def update_source(source_id: str, **fields) -> bool:
    """source_id 기준으로 지정 필드를 업데이트. 존재하지 않으면 False."""
    allowed = {
        "publisher",
        "rights_status",
        "quote_limit",
        "article_id",
        "language",
        "stance",
        "is_official",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT source_id FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        if row is None:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        params = list(updates.values()) + [source_id]
        conn.execute(f"UPDATE sources SET {set_clause} WHERE source_id = ?", params)
        conn.commit()
        return True
    finally:
        conn.close()


def get_source(source_id: str) -> dict | None:
    """claim_ids와 used_in_channels를 list로 반환한다."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
        if row is None:
            return None

        source = dict(row)
        source["claim_ids"] = json.loads(source["claim_ids"])
        source["used_in_channels"] = json.loads(source["used_in_channels"])
        return source
    finally:
        conn.close()


def mark_used(source_id: str, channel: str) -> None:
    """used_in_channels에 중복 없이 channel을 추가한다."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT used_in_channels FROM sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            return

        channels = json.loads(row["used_in_channels"])
        if channel not in channels:
            channels.append(channel)
            conn.execute(
                "UPDATE sources SET used_in_channels = ? WHERE source_id = ?",
                (json.dumps(channels, ensure_ascii=False), source_id),
            )
            conn.commit()
    finally:
        conn.close()


def list_sources(article_id: str) -> list[dict]:
    """article_id에 연결된 소스 목록을 반환한다."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM sources WHERE article_id = ? ORDER BY retrieved_at ASC",
            (article_id,),
        ).fetchall()
        sources: list[dict] = []
        for row in rows:
            source = dict(row)
            source["claim_ids"] = json.loads(source["claim_ids"])
            source["used_in_channels"] = json.loads(source["used_in_channels"])
            sources.append(source)
        return sources
    finally:
        conn.close()


def _cli_update(argv: list[str]) -> int:
    """python pipeline/source_registry.py update SRC_ID --stance con --language en ..."""
    import argparse

    parser = argparse.ArgumentParser(description="source 메타데이터 업데이트")
    parser.add_argument("source_id", help="업데이트할 source_id")
    parser.add_argument("--publisher")
    parser.add_argument("--rights-status", dest="rights_status")
    parser.add_argument("--quote-limit", dest="quote_limit", type=int)
    parser.add_argument("--article-id", dest="article_id")
    parser.add_argument("--language", choices=["ko", "en", "ja", "zh", "unknown"])
    parser.add_argument("--stance", choices=["pro", "neutral", "con", "unknown"])
    parser.add_argument("--is-official", dest="is_official", type=int, choices=[0, 1])
    args = parser.parse_args(argv)

    fields = {k: v for k, v in vars(args).items() if k != "source_id" and v is not None}
    ok = update_source(args.source_id, **fields)
    if ok:
        print(f"✓ {args.source_id} 업데이트 완료: {fields}")
        return 0
    print(f"✗ {args.source_id}를 찾을 수 없거나 변경할 필드가 없습니다.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # CLI: update 서브커맨드 지원 (TASK_019: stance 수동 override)
    if len(sys.argv) >= 2 and sys.argv[1] == "update":
        sys.exit(_cli_update(sys.argv[2:]))

    # 스모크 테스트: 기존 DB와 충돌하지 않도록 고유 식별자를 사용한다.
    test_suffix = uuid.uuid4().hex[:8]
    test_article_id = f"art-{test_suffix}"
    test_url = f"https://example.com/{test_suffix}"
    sid = add_source(url=test_url, publisher="Test", article_id=test_article_id)
    assert sid.startswith("src-")
    assert get_source(sid)["url"] == test_url
    duplicate_sid = add_source(url=test_url, publisher="Test", article_id=test_article_id)
    assert duplicate_sid == sid
    mark_used(sid, "web")
    mark_used(sid, "web")
    assert get_source(sid)["used_in_channels"] == ["web"]
    assert len(list_sources(test_article_id)) == 1

    # TASK_019: 확장 컬럼 동작 확인
    row = get_source(sid)
    assert "language" in row and "stance" in row and "is_official" in row
    assert row["stance"] == "neutral"
    assert row["is_official"] == 0
    assert update_source(sid, stance="pro", language="en", is_official=1) is True
    row2 = get_source(sid)
    assert row2["stance"] == "pro"
    assert row2["language"] == "en"
    assert row2["is_official"] == 1

    print("✓ source_registry 스모크 테스트 통과 (TASK_019 확장 컬럼 포함)")
