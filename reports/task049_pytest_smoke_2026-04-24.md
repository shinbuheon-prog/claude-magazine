# TASK_049 Pytest Smoke

Date: 2026-04-24

Commands:

```bash
python -m pytest -q tests
python -m py_compile pipeline/editorial_lint.py pipeline/citations_store.py tests/conftest.py tests/test_editorial_lint_article.py tests/test_editorial_lint_card_news.py tests/test_editorial_lint_integration.py
```

Result:

- `31 passed in 0.31s`
- Article-mode checks covered in pytest: 11
- Card-news checks covered in pytest: 4
- Integration coverage includes `--mode`, `--only`, `--strict`, JSON output, and citations_store round-trip
- Trace-based coverage fallback: `pipeline.editorial_lint 81.7%`, `pipeline.citations_store 80.6%`

Notes:

- The pytest run required execution outside the sandbox because Windows temp directory creation failed under sandbox restrictions.
- `pytest-cov` installation timed out repeatedly in this environment, so coverage was measured with `python -m trace --count --summary --missing`.
