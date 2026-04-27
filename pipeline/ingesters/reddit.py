from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_API_BASE = "https://oauth.reddit.com"
TIMEOUT = 15
_TOKEN_CACHE: dict[str, object] = {"token": None, "expires_at": 0.0}


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for Reddit ingestion")
    return value


def _get_oauth_token() -> str:
    now = time.time()
    token = _TOKEN_CACHE.get("token")
    expires_at = float(_TOKEN_CACHE.get("expires_at") or 0.0)
    if token and expires_at > now + 30:
        return str(token)

    client_id = _require_env("REDDIT_CLIENT_ID")
    client_secret = _require_env("REDDIT_CLIENT_SECRET")
    user_agent = _require_env("REDDIT_USER_AGENT")
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    request = urllib.request.Request(
        REDDIT_AUTH_URL,
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "User-Agent": user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    access_token = str(payload.get("access_token") or "")
    expires_in = int(payload.get("expires_in") or 3600)
    _TOKEN_CACHE["token"] = access_token
    _TOKEN_CACHE["expires_at"] = now + expires_in
    return access_token


def _keyword_match(text: str, keywords: list[str]) -> bool:
    haystack = (text or "").lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def fetch_top_posts(
    subreddits: list[str],
    keywords: list[str],
    since_days: int = 30,
    min_score: int = 20,
    max_results: int = 50,
) -> list[dict[str, object]]:
    token = _get_oauth_token()
    user_agent = _require_env("REDDIT_USER_AGENT")
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, since_days))
    results: list[dict[str, object]] = []

    for subreddit in subreddits:
        params = urllib.parse.urlencode({"t": "month", "limit": 100})
        url = f"{REDDIT_API_BASE}/r/{subreddit}/top?{params}"
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}", "User-Agent": user_agent},
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))

        for child in ((payload.get("data") or {}).get("children") or []):
            data = child.get("data") or {}
            score = int(data.get("score") or 0)
            created = datetime.fromtimestamp(float(data.get("created_utc") or 0), tz=timezone.utc)
            if score < min_score or created < cutoff:
                continue

            title = (data.get("title") or "").strip()
            selftext = (data.get("selftext") or "").strip()
            if not _keyword_match(f"{title}\n{selftext}", keywords):
                continue

            permalink = (data.get("permalink") or "").strip()
            results.append(
                {
                    "title": title,
                    "selftext": selftext,
                    "url": (data.get("url") or "").strip(),
                    "permalink": permalink,
                    "score": score,
                    "num_comments": int(data.get("num_comments") or 0),
                    "author": (data.get("author") or "").strip(),
                    "subreddit": (data.get("subreddit") or subreddit).strip(),
                    "created_at": created.isoformat(),
                }
            )

    results.sort(key=lambda item: (-int(item["score"]), -int(item["num_comments"])))
    return results[:max_results]


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch top Reddit posts")
    parser.add_argument("--subreddit", action="append", dest="subreddits")
    parser.add_argument("--keyword", action="append", dest="keywords")
    parser.add_argument("--since-days", type=int, default=30)
    parser.add_argument("--min-score", type=int, default=20)
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    subreddits = args.subreddits or ["ClaudeAI"]
    keywords = args.keywords or ["claude", "anthropic", "mcp"]
    posts = fetch_top_posts(
        subreddits=subreddits,
        keywords=keywords,
        since_days=args.since_days,
        min_score=args.min_score,
        max_results=args.max_results,
    )
    print(f"posts={len(posts)}")
    for post in posts[:5]:
        print(f"- r/{post['subreddit']}: {post['title']} ({post['score']})")
    if args.dry_run:
        print("dry-run complete")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(_cli())
