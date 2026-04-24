# TASK_044 Cache Smoke Report

Date: 2026-04-24

## Scenario

- Command 1:
  `python pipeline/fact_checker.py --draft drafts/task045_sample.md --article-id art-001 --out logs/task045_factcheck_1.md`
- Command 2:
  `python pipeline/fact_checker.py --draft drafts/task045_sample.md --article-id art-001 --out logs/task045_factcheck_2.md`

## Observed Usage

| Run | Request ID | Input Tokens | Output Tokens | Cache Write Tokens | Cache Read Tokens |
|---|---|---:|---:|---:|---:|
| 1 | `msg_01SDXFSxujNcbcYPXuHUWgKe` | 620 | 1414 | 3393 | 0 |
| 2 | `msg_013KtdNySVQvV5fmKWdmSLJb` | 6 | 1244 | 614 | 3393 |

## Result

- Cache hit confirmed on run 2.
- Fresh input tokens dropped from `620` to `6`.
- Cached prefix reuse was visible through `cache_read_input_tokens=3393`.
- Citations file was written both runs to `data/citations/art-001.json`.

## Additional Checks

- `brief_generator.py` real run completed and logged `cache_enabled=false` because the prompt stayed below threshold.
- `draft_writer.py` real run completed and logged `cache_enabled=false` for the same reason.

## Files

- `logs/factcheck_20260424_114651.json`
- `logs/factcheck_20260424_114924.json`
- `logs/brief_20260424_115315.json`
- `logs/draft_20260424_115305.json`
