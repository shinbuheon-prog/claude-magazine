# Monthly Publish Runbook

## Check Status

```bash
python scripts/publish_monthly.py --month 2026-05 --status
python scripts/publish_monthly.py --month 2026-05 --status --strict
```

Use `--strict` when incomplete stages should return exit code `1`.

## Reset One Stage

```bash
python scripts/publish_monthly.py --month 2026-05 --reset-stage quality_gate --yes
```

This removes the stage checkpoint and its telemetry from `reports/publish_state_2026-05.json`.

## Resume From A Stage

```bash
python scripts/publish_monthly.py --month 2026-05 --from-stage pdf_compile --dry-run --yes
```

This skips earlier stages and reruns from the selected stage onward.

## Full Dry Run

```bash
python scripts/publish_monthly.py --month 2026-05 --dry-run
```

## Notes

- Stage telemetry is stored under `telemetry` inside the publish state JSON.
- `quality_gate` and `ghost_publish` try to attach `cost_usd` when logs expose that signal.

## When A Stage Fails

- `publish_monthly.py` now writes `reports/failure_<month>_<stage>.md`
- Use the generated recovery guide first, then rerun:

```bash
python scripts/publish_monthly.py --month 2026-05 --reset-stage <stage> --yes
python scripts/publish_monthly.py --month 2026-05
```
