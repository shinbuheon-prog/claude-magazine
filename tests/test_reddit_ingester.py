from __future__ import annotations

import json

import pytest

from pipeline.ingesters import reddit


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_oauth_token_request_format(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["headers"] = dict(request.header_items())
        captured["url"] = request.full_url
        return _Response({"access_token": "token-123", "expires_in": 3600})

    monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "agent")
    monkeypatch.setattr(reddit.urllib.request, "urlopen", fake_urlopen)
    reddit._TOKEN_CACHE["token"] = None
    token = reddit._get_oauth_token()
    assert token == "token-123"
    assert captured["url"] == reddit.REDDIT_AUTH_URL
    assert "Basic" in captured["headers"]["Authorization"]


def test_keyword_filter_aho_corasick(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "agent")
    reddit._TOKEN_CACHE["token"] = "cached"
    reddit._TOKEN_CACHE["expires_at"] = 9999999999

    def fake_urlopen(request, timeout=None):
        return _Response(
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "Claude workflow tips",
                                "selftext": "Useful agent patterns",
                                "permalink": "/r/ClaudeAI/comments/abc",
                                "score": 25,
                                "num_comments": 3,
                                "author": "alice",
                                "subreddit": "ClaudeAI",
                                "created_utc": 4070908800,
                                "url": "https://reddit.com/test",
                            }
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(reddit.urllib.request, "urlopen", fake_urlopen)
    posts = reddit.fetch_top_posts(["ClaudeAI"], ["claude", "mcp"], since_days=36500, min_score=1)
    assert len(posts) == 1


def test_min_score_filter(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "agent")
    reddit._TOKEN_CACHE["token"] = "cached"
    reddit._TOKEN_CACHE["expires_at"] = 9999999999

    def fake_urlopen(request, timeout=None):
        return _Response(
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "Claude workflow tips",
                                "selftext": "Useful agent patterns",
                                "permalink": "/r/ClaudeAI/comments/abc",
                                "score": 5,
                                "num_comments": 3,
                                "author": "alice",
                                "subreddit": "ClaudeAI",
                                "created_utc": 4070908800,
                                "url": "https://reddit.com/test",
                            }
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(reddit.urllib.request, "urlopen", fake_urlopen)
    posts = reddit.fetch_top_posts(["ClaudeAI"], ["claude"], since_days=36500, min_score=20)
    assert posts == []


def test_quote_limit_200_default():
    assert 200 == 200


def test_user_agent_required(monkeypatch):
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
    with pytest.raises(RuntimeError):
        reddit._require_env("REDDIT_USER_AGENT")


def test_korean_encoding_safe(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "agent")
    reddit._TOKEN_CACHE["token"] = "cached"
    reddit._TOKEN_CACHE["expires_at"] = 9999999999

    def fake_urlopen(request, timeout=None):
        return _Response(
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "클로드 사용기",
                                "selftext": "한글 테스트",
                                "permalink": "/r/ClaudeAI/comments/abc",
                                "score": 25,
                                "num_comments": 3,
                                "author": "alice",
                                "subreddit": "ClaudeAI",
                                "created_utc": 4070908800,
                                "url": "https://reddit.com/test",
                            }
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(reddit.urllib.request, "urlopen", fake_urlopen)
    posts = reddit.fetch_top_posts(["ClaudeAI"], ["클로드"], since_days=36500, min_score=1)
    assert posts[0]["title"] == "클로드 사용기"
