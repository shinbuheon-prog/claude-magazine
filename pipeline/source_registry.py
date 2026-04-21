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
    article_id       TEXT DEFAULT ''
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _hash_content(content_preview: str) -> str:
    return hashlib.sha256(content_preview.encode("utf-8")).hexdigest()[:8]


def add_source(
    url,
    publisher="",
    content_preview="",
    rights_status="unknown",
    quote_limit=200,
    article_id="",
) -> str:
    """이미 등록된 URL이면 기존 source_id를 반환한다."""
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT source_id FROM sources WHERE url = ?", (url,)).fetchone()
        if existing:
            return existing["source_id"]

        source_id = f"src-{uuid.uuid4().hex[:8]}"
        retrieved_at = datetime.now(timezone.utc).isoformat()
        version_hash = _hash_content(content_preview) if content_preview else ""

        conn.execute(
            """
            INSERT INTO sources (
                source_id, url, publisher, retrieved_at, version_hash,
                rights_status, quote_limit, article_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
        return source_id
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


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sid = add_source(url="https://example.com", publisher="Test", article_id="art-001")
    assert sid.startswith("src-")
    assert get_source(sid)["url"] == "https://example.com"
    duplicate_sid = add_source(url="https://example.com", publisher="Test", article_id="art-001")
    assert duplicate_sid == sid
    mark_used(sid, "web")
    mark_used(sid, "web")
    assert get_source(sid)["used_in_channels"] == ["web"]
    assert len(list_sources("art-001")) == 1
    print("✓ source_registry 스모크 테스트 통과")
