# Current Task: nightly-ensure-env

**Complexity:** Level 1

## Fix

The nightly payload was `(date; stockroom ingest && stockroom embed)`. An exact `uv sync` (from `make test`, `make format`, and the pre-commit hook) uninstalls torch, and the unattended job never ran `stockroom shim ensure-env`, so embed died with `ModuleNotFoundError: No module named 'torch'` while ingest had already succeeded.

`render_payload` now renders `(date; stockroom shim ensure-env; stockroom ingest && stockroom embed)`. The `;` keeps a failed heal from skipping ingest. The `&&` still skips embed when ingest fails. Cron and launchd both use that one payload, so `schedule status` reports a pre-change entry as `up-to-date: no`.

## Files

- `skills/sr-search/src/stockroom/schedule.py`
- `skills/sr-search/tests/test_schedule.py`
- `skills/sr-search/src/stockroom/__main__.py`
- `skills/sr-search/src/stockroom/backfill/__main__.py`
- `skills/sr-initialize/SKILL.md`
- `docs/architecture/backfill.md`
- `docs/architecture/index.md`
- `docs/architecture/lifecycle.md`
- `docs/user-guide/load/schedule.md`
