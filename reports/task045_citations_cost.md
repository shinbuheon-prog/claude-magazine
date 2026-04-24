# TASK_045 Citations Cost

Date: 2026-04-24

Cost estimate uses Anthropic's published prompt caching rates for Claude Opus 4.7:

- Base input: `$5 / MTok`
- 5-minute cache write: `$6.25 / MTok`
- Cache read: `$0.50 / MTok`
- Output: `$25 / MTok`

## Measured Runs

| Run | Input | Cache Write | Cache Read | Output | Estimated Cost |
|---|---:|---:|---:|---:|---:|
| 1 | 620 | 3393 | 0 | 1414 | `$0.0597` |
| 2 | 6 | 614 | 3393 | 1244 | `$0.0367` |

## Interpretation

- First run pays the main document-cache write cost.
- Second run is materially cheaper on the prompt side because the 3393-token reusable prefix is read from cache instead of being billed as regular uncached input.
- Two-run total for this sample was approximately `$0.0963`.

## Rough Editorial Projection

If a single fact-check pass looks similar to run 1, then:

- 1 article: about `$0.06`
- 21 articles in one issue: about `$1.25`
- 4 issues per month: about `$5.00`

This excludes retries, failed fetches, and any additional comparison passes.
