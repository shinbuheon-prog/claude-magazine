from __future__ import annotations


from pipeline.ingesters import arxiv


ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2511.02824v1</id>
    <published>2026-04-01T12:00:00Z</published>
    <title>Claude planning for AI agents</title>
    <summary>Anthropic studies constitutional ai planning.</summary>
    <author><name>Jane Doe</name></author>
    <author><name>홍길동</name></author>
    <link href="http://arxiv.org/abs/2511.02824v1" />
    <link title="pdf" href="http://arxiv.org/pdf/2511.02824v1" type="application/pdf" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2511.99999v1</id>
    <published>2026-04-01T12:00:00Z</published>
    <title>Unrelated database paper</title>
    <summary>No relevant agent mention here.</summary>
    <author><name>Someone Else</name></author>
    <link href="http://arxiv.org/abs/2511.99999v1" />
  </entry>
</feed>
"""


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return ATOM_SAMPLE.encode("utf-8")


def test_fetch_recent_papers_returns_list(monkeypatch):
    monkeypatch.setattr(arxiv.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    papers = arxiv.fetch_recent_papers("claude OR anthropic", since_days=36500, max_results=10)
    assert isinstance(papers, list)
    assert len(papers) == 1


def test_keyword_filter_excludes_non_claude(monkeypatch):
    monkeypatch.setattr(arxiv.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    papers = arxiv.fetch_recent_papers("claude", since_days=36500, max_results=10)
    assert all("claude" in (paper["title"] + " " + paper["abstract"]).lower() for paper in papers)


def test_since_days_filtering(monkeypatch):
    monkeypatch.setattr(arxiv.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    papers = arxiv.fetch_recent_papers("claude", since_days=1, max_results=10)
    assert papers == []


def test_arxiv_id_format(monkeypatch):
    monkeypatch.setattr(arxiv.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    paper = arxiv.fetch_recent_papers("claude", since_days=36500, max_results=10)[0]
    assert paper["arxiv_id"].startswith("2511.02824")


def test_korean_encoding_safe(monkeypatch):
    monkeypatch.setattr(arxiv.urllib.request, "urlopen", lambda *args, **kwargs: _Response())
    paper = arxiv.fetch_recent_papers("claude", since_days=36500, max_results=10)[0]
    assert "홍길동" in paper["authors"]
