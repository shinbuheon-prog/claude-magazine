from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HN_API_BASE = "https://hn.algolia.com/api/v1/search"
TIMEOUT = 15


def _keyword_match(text: str, query: str) -> bool:
    haystack = (text or "").lower()
    parts = [part.strip().strip('"') for part in query.lower().replace("(", " ").replace(")", " ").split("or")]
    tokens = [part for part in parts if part and part not in {"and"}]
    return any(token in haystack for token in tokens) if tokens else True


def fetch_top_stories(
    query: str,
    since_days: int = 30,
    min_points: int = 10,
    max_results: int = 50,
) -> list[dict[str, object]]:
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=max(0, since_days))).timestamp())
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"points>={int(min_points)},created_at_i>{cutoff}",
        "hitsPerPage": max(1, min(int(max_results), 1000)),
    }
    url = f"{HN_API_BASE}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "claude-magazine/1.0"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))

    hits = payload.get("hits") or []
    results: list[dict[str, object]] = []
    for hit in hits:
        title = (hit.get("title") or hit.get("story_title") or "").strip()
        story_text = (hit.get("story_text") or hit.get("comment_text") or "").strip()
        if not title:
            continue
        created_at = (hit.get("created_at") or "").strip()
        if created_at:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created_dt < (datetime.now(timezone.utc) - timedelta(days=max(0, since_days))):
                continue
        if int(hit.get("points") or 0) < min_points:
            continue
        if not _keyword_match(f"{title}\n{story_text}", query):
            continue

        story_id = str(hit.get("objectID") or "")
        results.append(
            {
                "title": title,
                "url": (hit.get("url") or "").strip(),
                "points": int(hit.get("points") or 0),
                "num_comments": int(hit.get("num_comments") or 0),
                "author": (hit.get("author") or "").strip(),
                "created_at": created_at,
                "story_id": story_id,
                "story_url": f"https://news.ycombinator.com/item?id={story_id}",
                "text": story_text,
            }
        )
    results.sort(key=lambda item: (-int(item["points"]), -int(item["num_comments"])))
    return results[:max_results]


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch top Hacker News stories")
    parser.add_argument("--query", required=True)
    parser.add_argument("--since-days", type=int, default=30)
    parser.add_argument("--min-points", type=int, default=10)
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    stories = fetch_top_stories(
        query=args.query,
        since_days=args.since_days,
        min_points=args.min_points,
        max_results=args.max_results,
    )
    print(f"stories={len(stories)}")
    for story in stories[:5]:
        print(f"- {story['story_id']}: {story['title']} ({story['points']} pts)")
    if args.dry_run:
        print("dry-run complete")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(_cli())
