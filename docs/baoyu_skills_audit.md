# baoyu Skills Audit

- Source repository: `jimliu/baoyu-skills`
- Source commit: `8c17d77209b030a97d1746928ae348c99fefa775`
- Imported wrappers:
  - `baoyu-url-to-markdown`
  - `baoyu-youtube-transcript`
  - `baoyu-article-illustrator`
  - `baoyu-infographic`

## License

- Upstream repository README declares `MIT`.
- The cloned tree used for TASK_040 did not include a root `LICENSE` file, so this project records the license claim from upstream README plus repository metadata.

## Local Adaptation

- The local `.claude/skills/baoyu-*` files are Korean magazine wrappers, not byte-for-byte copies.
- Each wrapper includes:
  - Korean usage guidance
  - project-relative commands
  - upstream commit provenance comment
  - verification checklist compatible with this repository's `validate_skills.py`

## Integration Notes

- `source_ingester.py` now accepts `type: url` and `type: youtube`.
- URL ingestion writes markdown snapshots to `drafts/ingested/url/`.
- YouTube ingestion writes metadata-first placeholder markdown to `drafts/ingested/youtube/`.
- `draft_writer.py --illustrate` now routes through `pipeline/illustration_hook.py`.
- `illustration_hook.py` creates prompt files, placeholder PNGs, and `logs/illustrations.jsonl`.
- `InsightPage.jsx` now supports `comparison`, `timeline`, and `process-flow` layouts in addition to the existing chart.

## Validation

- Recommended command:
  - `python scripts/validate_skills.py --skill baoyu-url-to-markdown --lang ko`
  - repeat for the other three wrappers
- Build check:
  - `cd web && npm run build`

## Known Limits

- Actual upstream baoyu runtimes are not embedded in this repository.
- YouTube transcript extraction is metadata-first unless the external runtime is attached later.
- Article illustration currently generates placeholder review assets until an image backend is wired in.
