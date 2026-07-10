# Active Context

## Current Task: fix-dashboard-utc-timestamps
**Phase:** BUILD - COMPLETE

## What Was Done
- UTC-at-rest contract: `stockroom.timestamps`, discovery mtime, Claude `_parse_ts`, writer/metrics `utc_now`
- Migration `0005` clears `_sync_state` watermarks; metrics `_iso` emits `Z`; dashboard `parseDisplayDate` treats warehouse datetimes as UTC
- Wrapped peak labeled "Peak Hour (UTC)"; full suite green (491 passed, 3 skipped)

## Files modified
- `skills/sr-search/src/stockroom/timestamps.py` (new)
- `skills/sr-search/src/stockroom/ingest/sources.py`, `claude.py`, `writer.py`, `model.py`
- `skills/sr-search/src/stockroom/dashboard/metrics.py`
- `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`, `dashboard.mjs`, `index.html`
- `skills/sr-search/src/stockroom/migrations/0005_utc_timestamps.sql` (new)
- Tests under `tests/` and `tests-js/`

## Key decisions
- Naive DuckDB TIMESTAMP = UTC; wire format uses `Z`; no TIMESTAMPTZ
- Watermark clear instead of SQL conversion of historical local mtimes

## Next Step
- QA review (automatic per Level 2 workflow)
