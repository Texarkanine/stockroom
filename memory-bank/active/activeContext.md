# Active Context

## Current Task: warehouse-file-growth, milestone 5 (verified newer-format copy)
**Phase:** BUILD - COMPLETE

## What Was Done
- `apply_pending` and `build_warehouse` take keyword-only `through`. The default still applies every later migration
- `copy_warehouse` leaves `warehouse.copy.duckdb` beside the original, built from the schema file through the original's version, filled with the original's rows, and checked on a fresh read-only connection. It returns sizes and times. It does not take the flock or replace the original
- A populated `messages.text` or `tool_calls.tool_input` must have zstd data segments. An empty column has none and does not fail the check
- Files: `migrate.py`, `storage.py`, `test_migrate_runner.py`, `test_storage.py`, `_warehouse_worker.py`, `conftest.py`
- Engine pytest: 1110 passed, 36 skipped, with torch installed. Coverage-collection: 4 passed. Dashboard JS: 134 passed. Ruff, schema docs, released migrations, and REUSE passed
- Nanobind leak lines at pytest exit are the known torch-in-process noise

## Next Step
- QA review runs automatically
