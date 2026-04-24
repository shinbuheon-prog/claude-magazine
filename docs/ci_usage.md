# CI Usage Guide

## Scope

`TASK_052` expands `.github/workflows/ci.yml` into parallel jobs for:

- `python-lint`
- `python-smoke`
- `python-tests`
- `web-build`
- `env-check`
- `spec-lint`
- `mojibake-scan`

`codex_sync.yml` stays unchanged.

## Free Tier Notes

- Public repositories can usually run GitHub Actions without the private-repo minute cap.
- Private repositories on the free tier are limited by monthly action minutes. The common baseline is 2,000 minutes per month, but billing policy can change, so verify the current GitHub plan page before relying on it.
- This workflow keeps costs down with `paths-ignore` for markdown-only changes and by limiting `push` runs to `main` and `develop`.

## Branch Protection

Set branch protection for `main` in GitHub:

1. Open `Settings -> Branches -> Add rule`.
2. Target branch pattern: `main`.
3. Enable `Require a pull request before merging`.
4. Enable `Require branches to be up to date before merging`.
5. Require these status checks:
   - `python-lint`
   - `python-smoke`
   - `python-tests`
   - `web-build`
   - `env-check`
   - `spec-lint`
   - `mojibake-scan`
6. Optionally enable `Include administrators`.

`develop` can stay less strict if it remains the active integration branch.

## Job Notes

- `python-smoke` checks `codex_workflow.py list`, `source_registry.py`, and import smoke for `brief_generator` and `fact_checker`.
- `python-tests` publishes `coverage.xml` as an artifact.
- `env-check` uses `.env.example` and `--dry-run`, so it validates structure without requiring real secrets.
- `spec-lint` validates YAML parsing and `failure_playbook` structure.
- `mojibake-scan` only fails on replacement-character markers to avoid broad false positives from legacy text.
