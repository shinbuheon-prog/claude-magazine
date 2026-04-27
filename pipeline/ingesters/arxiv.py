from __future__ import annotations

import argparse
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ARXIV_API_BASE = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}
TIMEOUT = 15


def _build_query(query: str, category: str) -> str:
    cleaned = " ".join((query or "").strip().split())
    return f"cat:{category} AND ({cleaned})" if cleaned else f"cat:{category}"


def _safe_text(node: ET.Element | None, path: str) -> str:
    if node is None:
        return ""
    found = node.find(path, NS)
    return (found.text or "").strip() if found is not None and found.text else ""


def _extract_arxiv_id(entry: ET.Element) -> str:
    raw = _safe_text(entry, "atom:id")
    if raw.rstrip("/").split("/")[-1]:
        return raw.rstrip("/").split("/")[-1]
    return ""


def _keyword_match(text: str, query: str) -> bool:
    haystack = (text or "").lower()
    parts = [part.strip().strip('"') for part in query.lower().replace("(", " ").replace(")", " ").split("or")]
    tokens = [part for part in parts if part and part not in {"and"}]
    return any(token in haystack for token in tokens) if tokens else True


def fetch_recent_papers(
    query: str,
    category: str = "cs.AI",
    since_days: int = 30,
    max_results: int = 100,
) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, since_days))
    params = {
        "search_query": _build_query(query, category),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max(1, min(int(max_results), 300)),
    }
    url = f"{ARXIV_API_BASE}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "claude-magazine/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    results: list[dict[str, object]] = []
    for entry in root.findall("atom:entry", NS):
        published_raw = _safe_text(entry, "atom:published")
        if not published_raw:
            continue
        published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        if published < cutoff:
            continue

        title = " ".join(_safe_text(entry, "atom:title").split())
        abstract = " ".join(_safe_text(entry, "atom:summary").split())
        combined = f"{title}\n{abstract}"
        if not _keyword_match(combined, query):
            continue

        authors = [
            " ".join((author.findtext("atom:name", default="", namespaces=NS) or "").split())
            for author in entry.findall("atom:author", NS)
        ]
        pdf_link = ""
        for link in entry.findall("atom:link", NS):
            href = (link.attrib.get("href") or "").strip()
            if href and link.attrib.get("type") == "application/pdf":
                pdf_link = href
                break
        if not pdf_link:
            pdf_link = _safe_text(entry, "atom:id")

        results.append(
            {
                "title": title,
                "abstract": abstract,
                "authors": [author for author in authors if author],
                "link": pdf_link,
                "published": published.isoformat(),
                "arxiv_id": _extract_arxiv_id(entry),
                "category": category,
            }
        )
    return results


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch recent arXiv papers")
    parser.add_argument("--query", required=True)
    parser.add_argument("--category", default="cs.AI")
    parser.add_argument("--since-days", type=int, default=30)
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    papers = fetch_recent_papers(
        query=args.query,
        category=args.category,
        since_days=args.since_days,
        max_results=args.max_results,
    )
    print(f"papers={len(papers)}")
    for paper in papers[:5]:
        print(f"- {paper['arxiv_id']}: {paper['title']}")
    if args.dry_run:
        print("dry-run complete")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(_cli())
