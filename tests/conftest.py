from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline import citations_store, editorial_lint


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DummyProviderResult:
    def __init__(self, text: str) -> None:
        self.text = text


class DummyProvider:
    name = "mock"

    def __init__(self, text: str = "88") -> None:
        self._text = text

    def count_tokens(self, **_: object) -> int:
        return 32

    def complete_with_blocks(self, **_: object) -> DummyProviderResult:
        return DummyProviderResult(self._text)


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    logs_dir = tmp_path / "logs"
    citations_dir = tmp_path / "citations"
    logs_dir.mkdir()
    citations_dir.mkdir()
    monkeypatch.setattr(editorial_lint, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(citations_store, "CITATIONS_DIR", citations_dir)


@pytest.fixture
def fixture_text() -> callable:
    def _reader(*parts: str) -> str:
        return (FIXTURES_DIR.joinpath(*parts)).read_text(encoding="utf-8")

    return _reader


@pytest.fixture
def fixture_json() -> callable:
    def _reader(*parts: str) -> dict:
        return json.loads((FIXTURES_DIR.joinpath(*parts)).read_text(encoding="utf-8"))

    return _reader


@pytest.fixture
def dummy_provider() -> DummyProvider:
    return DummyProvider("92")
