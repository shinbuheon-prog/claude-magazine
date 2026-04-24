# TASK_044 Cache Scope

Date: 2026-04-24

Measured with Anthropic token counting on the current implementation.

## Token Counts

| Pipeline | Model Tier | Measured Tokens | Cache Threshold | Decision |
|---|---:|---:|---:|---|
| `fact_checker.py` plain prompt path | Opus 4.7 | 1223 | 4096 | Plain prompt alone is below threshold |
| `fact_checker.py` document+citation path | Opus 4.7 | n/a via preflight count | 4096 | Actual live run produced `cache_creation_input_tokens=3393`, confirming the cached prefix became eligible once source documents were attached |
| `editorial_lint.py` title-body-match | Sonnet 4.6 | 252 | 2048 | Skip caching |
| `brief_generator.py` | Sonnet 4.6 | 617 | 2048 | Skip caching |
| `draft_writer.py` | Sonnet 4.6 | 735 | 2048 | Skip caching |

## Notes

- Prompt caching thresholds were checked against Anthropic's official prompt caching docs for active models.
- `fact_checker.py` now uses explicit cache breakpoints on:
  - the reusable system/heuristics block
  - the last reusable document block in the citations path
- `brief_generator.py`, `draft_writer.py`, and `editorial_lint.py` now measure prompt size and only attach `cache_control` when the request is large enough. Current representative runs stay below the Sonnet threshold, so they log `cache_enabled=false`.

## Verification

- Token count API used through `pipeline/claude_provider.py`
- Representative draft: `drafts/task045_sample.md`
- Representative brief: `drafts/brief_20260421_172333.json`
