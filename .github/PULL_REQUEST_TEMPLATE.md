## Change Summary
<!-- What changed and why? Keep this to a few lines. -->

## Related Issue
- Closes #

## Change Type
- [ ] Task implementation (`TASK_XXX`)
- [ ] Pipeline behavior change
- [ ] Bug fix
- [ ] Documentation update
- [ ] Other

---

## Editorial Checklist
- [ ] Every claim still maps to a valid `source_id`
- [ ] No translation-only or summary-only rewrite drift
- [ ] Headline and body still match without exaggeration
- [ ] AI disclosure and correction policy are preserved where required
- [ ] Claude API calls still log `request_id`
- [ ] No secrets or `.env` values were committed

## Verification
- [ ] `python codex_workflow.py list`
- [ ] Relevant Python tests or smoke commands passed
- [ ] `npm run build` passed for `web/` changes
- [ ] CI checks passed or are expected to pass after merge queue
