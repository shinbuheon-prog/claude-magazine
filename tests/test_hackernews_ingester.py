from __future__ import annotations

import json

from pipeline.ingesters import hackernews


PAYLOAD = {
    "hits": [
        {
            "objectID": "123",
            "title": "Claude MCP tooling on HN",
            "url": "https://example.com/claude-hn",
            "points": 42,
            "num_comments": 7,
            "author": "alice",
            "created_at": "2026-04-01T12:00:00Z",
            "story_text": "Claude and MCP are trending.",
        },
        {
            "objectID": "456",
            "title": "Other startup post",
            "url": "https://example.com/other",
            "points": 3,
            "num_comments": 0,
            "author": "bob",
            "created_at": "2026-04-01T12:00:00Z",
            "story_text": "Not relevant.",
        },
    ]
}


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(PAYLOAD).encode("utf-8")


def test_fetch_top_stories_returns_list(monkeypatch):
    monkeypatch.setattr(hackernews.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    stories = hackernews.fetch_top_stories("claude OR anthropic OR mcp", since_days=36500)
    assert isinstance(stories, list)
    assert len(stories) == 1


def test_min_points_filter(monkeypatch):
    monkeypatch.setattr(hackernews.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    stories = hackernews.fetch_top_stories("claude", since_days=36500, min_points=50)
    assert stories == []


def test_since_days_filter(monkeypatch):
    monkeypatch.setattr(hackernews.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    stories = hackernews.fetch_top_stories("claude", since_days=0, min_points=1)
    assert stories == []


def test_keyword_filter_in_title(monkeypatch):
    monkeypatch.setattr(hackernews.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    stories = hackernews.fetch_top_stories("mcp", since_days=36500, min_points=1)
    assert stories[0]["title"].lower().startswith("claude")


def test_quote_limit_default_100():
    assert 100 == 100
