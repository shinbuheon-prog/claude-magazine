"""
출처 레지스트리 — SQLite 기반 소스 추적 시스템
MVP: SQLite / 이후 Supabase(Postgres) 전환 가능 인터페이스
"""
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
DB_PATH = Path(os.environ.get("SOURCE_DB_PATH", str(ROOT / "data" / "source_registry.db")))
DB_PATH.parent.mkdir(exist_ok=True)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    source_id       TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    publisher       TEXT,
    retrieved_at    TEXT,
    version_hash    TEXT,
    rights_status   TEXT DEFAULT 'unknown',
    claim_ids       TEXT DEFAULT '[]',
    quote_limit     INTEGER DEFAULT 200,
    used_in_channels TEXT DEFAULT '[]',
    article_id      TEXT
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def add_source(
    url: str,
    publisher: str = "",
    content_preview: str = "",
    rights_status: str = "unknown",
    quote_limit: int = 200,
    article_id: str = "",
) -> str:
    """소스 등록. 이미 등록된 URL이면 기존 source_id 반환."""
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT source_id FROM sources WHERE url = ?", (url,)).fetchone()
        if existing:
            return existing["source_id"]

        source_id = f"src-{uuid.uuid4().hex[:8]}"
        version_hash = _hash_content(content_preview) if content_preview else ""
        retrieved_at = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """INSERT INTO sources
               (source_id, url, publisher, retrieved_at, version_hash,
                rights_status, quote_limit, article_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_id, url, publisher, retrieved_at, version_hash,
             rights_status, quote_limit, article_id),
        )
        conn.commit()
        return source_id
    finally:
        conn.close()


def get_source(source_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["claim_ids"] = json.loads(d["claim_ids"])
        d["used_in_channels"] = json.loads(d["used_in_channels"])
        return d
    finally:
        conn.close()


def mark_used(source_id: str, channel: str) -> None:
    """used_in_channels에 채널 추가 (중복 제거)"""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT used_in_channels FROM sources WHERE source_id = ?", (source_id,)).fetchone()
        if not row:
            return
        channels = json.loads(row["used_in_channels"])
        if channel not in channels:
            channels.append(channel)
        conn.execute(
            "UPDATE sources SET used_in_channels = ? WHERE source_id = ?",
            (json.dumps(channels), source_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_sources(article_id: str) -> list[dict]:
    """기사 ID로 소스 목록 조회"""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM sources WHERE article_id = ?", (article_id,)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["claim_ids"] = json.loads(d["claim_ids"])
            d["used_in_channels"] = json.loads(d["used_in_channels"])
            result.append(d)
        return result
    finally:
        conn.close()


if __name__ == "__main__":
    # 스모크 테스트
    sid = add_source(
        url="https://www.anthropic.com/news/claude-4",
        publisher="Anthropic",
        content_preview="Claude 4 release notes sample text",
        article_id="article-test-001",
    )
    print(f"등록된 source_id: {sid}")
    print(f"조회: {get_source(sid)}")
    mark_used(sid, "web")
    mark_used(sid, "email")
    print(f"사용 표기 후: {get_source(sid)['used_in_channels']}")
    print(f"기사별 소스: {list_sources('article-test-001')}")
