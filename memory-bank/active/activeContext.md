# Active Context

## Current Task: fix-cursor-cli-wal-ingest
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented `_read_store` with `mode=ro` → `immutable=1` fallback; wired `parse_session`
- Added WAL-at-rest, live-sidecars, fallback-retry (mocked lazy-open failure), and corrupt-file tests
- Full suite: 789 passed, 2 skipped
- Note: bare `mode=ro` failure on checkpointed WAL was not reproducible on this machine's SQLite 3.37.2 / 3.50.4; fallback still implemented per #95; regression covered via mock

## Next Step
- Enter Level 1 QA (`niko-qa`)
