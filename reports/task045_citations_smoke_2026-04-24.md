# TASK_045 Citations Smoke Report

Date: 2026-04-24

## Generated Artifacts

- Citations store:
  `data/citations/art-001.json`
- Fact-check outputs:
  `logs/task045_factcheck_1.md`
  `logs/task045_factcheck_2.md`

## Cases

### Pass

- Command:
  `python pipeline/editorial_lint.py --draft drafts/task045_pass.md --article-id art-001 --json`
- Result:
  `citations-cross-check = pass`
- Note:
  The draft only referenced `src-754e2e39` and `src-e1bdbaa1`, which both appeared in the generated citations payload.

### Warn

- Command:
  `python pipeline/editorial_lint.py --draft drafts/task045_sample.md --article-id art-missing --json`
- Result:
  `citations-cross-check = warn`
- Note:
  No citations file existed for that article id, so the check degraded without blocking publish.

### Warn (mismatch)

- Command:
  `python pipeline/editorial_lint.py --draft drafts/task045_sample.md --article-id art-001 --json`
- Result:
  `citations-cross-check = warn`
- Missing IDs:
  `src-0e919e71`, `src-72fbf5a5`
- Note:
  The citations payload only contained document-backed evidence for the successfully fetched source documents. The manual draft claimed more source ids than the citations output could support, which is now treated as a non-blocking rollout warning.

## Residual Risk

- Citation quality still depends on source fetch success before the Anthropic call.
- This implementation intentionally keeps the old manual `source_id` path and adds citations as a parallel validation layer rather than replacing it.
