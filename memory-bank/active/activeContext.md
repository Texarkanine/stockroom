# Active Context

## Current Task: fix-pr152-check-blockers
**Phase:** PLAN - COMPLETE

## What Was Done
- Wrote the Level 2 plan for the two pull request 152 blockers
- Session-start check token becomes `PYTHONPATH="$APP/src" "$APP/.venv/bin/python" -m stockroom.check` in both hook files, with the packaging tests updated first
- Lifecycle item 3 names that interpreter. `check.launch` stays on `sys.executable`
- `_catalog` drops `table_sql`. A new test copies a `released_chain_154(8)` warehouse after `warehouse.open` migrates it to schema 9
- Stop if that copy fails on a catalog part other than `table_sql`, or if migration removes `CAST('f' AS BOOLEAN)`

## Next Step
- Preflight validation of this plan
