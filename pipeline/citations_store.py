from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CITATIONS_DIR = ROOT / "data" / "citations"


def _normalize_citation(citation: Any, document_map: list[dict[str, Any]]) -> dict[str, Any]:
    if hasattr(citation, "model_dump"):
        payload = citation.model_dump()
    elif hasattr(citation, "to_dict"):
        payload = citation.to_dict()
    elif isinstance(citation, dict):
        payload = dict(citation)
    else:
        payload = {
            key: getattr(citation, key)
            for key in dir(citation)
            if not key.startswith("_") and not callable(getattr(citation, key))
        }

    doc_index = payload.get("document_index")
    mapped = document_map[doc_index] if isinstance(doc_index, int) and 0 <= doc_index < len(document_map) else {}
    return {
        "type": payload.get("type"),
        "document_index": doc_index,
        "document_title": payload.get("document_title"),
        "source_id": mapped.get("source_id"),
        "url": mapped.get("url"),
        "char_start": payload.get("start_char_index"),
        "char_end": payload.get("end_char_index"),
        "block_start": payload.get("start_block_index"),
        "block_end": payload.get("end_block_index"),
        "page_start": payload.get("start_page_number"),
        "page_end": payload.get("end_page_number"),
        "quote": payload.get("cited_text"),
    }


def extract_claims(raw_response: Any, document_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for idx, block in enumerate(getattr(raw_response, "content", []) or []):
        text = getattr(block, "text", None)
        if not text:
            continue
        citations = getattr(block, "citations", None) or []
        claims.append(
            {
                "claim_idx": idx,
                "text": text,
                "citations": [_normalize_citation(citation, document_map) for citation in citations],
            }
        )
    return claims


def save_citations(
    *,
    article_id: str,
    request_id: str | None,
    provider: str,
    model: str,
    document_map: list[dict[str, Any]],
    raw_response: Any,
) -> Path:
    CITATIONS_DIR.mkdir(parents=True, exist_ok=True)
    claims = extract_claims(raw_response, document_map)
    payload = {
        "article_id": article_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "provider": provider,
        "model": model,
        "document_map": document_map,
        "claims": claims,
    }
    path = CITATIONS_DIR / f"{article_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_citations(article_id: str) -> dict[str, Any] | None:
    path = CITATIONS_DIR / f"{article_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
