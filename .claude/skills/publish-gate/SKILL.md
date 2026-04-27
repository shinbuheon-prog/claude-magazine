---
name: publish-gate
description: Integrates editorial_lint, standards_checker, source_diversity, G2, disclosure injection, and quality_review before publication.
allowed-tools: Bash, Read, Edit
---

# Publish Gate

## When to use
- The user asks for a final publish check.
- A Ghost draft is about to be changed to `published`.
- The team needs a single go/no-go gate across all editorial checks.

## Workflow

### 1. editorial_lint
```bash
python pipeline/editorial_lint.py --draft {draft_path} --strict --json
```
- Stop immediately on failure.

### 2. standards_checker
```bash
python pipeline/standards_checker.py --draft {draft_path} --category {category}
```
- All `must_pass` items must pass.

### 3. source_diversity
```bash
python pipeline/source_diversity.py --article-id {article_id} --strict
```
- This now enforces 5 rules, including the triple pattern:
  - Korean official source >= 1
  - English official source >= 1
  - Opposing or affected source >= 1

### 3.5 G2 gate
```bash
python pipeline/g2_gate.py --article-id {article_id} --strict --json
```
- `confirmed_ratio >= 0.85`: pass
- `0.5 <= confirmed_ratio < 0.85`: editor G2 review required, exit 1
- `confirmed_ratio < 0.5`: block publish, exit 2

### 4. AI disclosure injection
```bash
python pipeline/disclosure_injector.py --html {html_path} --template {heavy|light|interview}
```
- Or update Ghost directly:
```bash
python pipeline/disclosure_injector.py --ghost-post-id {id} --template heavy
```

### 5. Comprehensive quality review
```bash
python pipeline/quality_review.py --draft {draft_path} --article-id {article_id} --strict --json > logs/quality_review_{article_id}.json
```
- `pass`: continue
- `partial`: manual editor review and fix required
- `fail`: block publish and rewrite recommended

### 6. Final handoff
- Report each gate result.
- Explicitly state whether publication is allowed.
- Do not auto-publish. Human confirmation is still required.

## Verify before success
- `editorial_lint` passed
- `standards_checker` must-pass items passed
- `source_diversity` passed all 5 rules, or approved exception documented
- `g2_gate` did not return review/block without editor action
- disclosure injection applied
- `quality_review` completed and verdict recorded

## Notes
- Never auto-publish from this skill.
- Keep the gate logs in `logs/`.
