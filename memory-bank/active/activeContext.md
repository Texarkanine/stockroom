# Active Context

## Current Task: workspace-key
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented Option C `workspace_key` end-to-end (paths registry, migration 0006, writer, metrics rollup, docs)
- Head-version pins also bumped in `test_warehouse_open` / `test_warehouse_concurrency` (beyond migrate_runner)
- `make format && make lint && make test` green (524 passed / 3 skipped; JS 61)

## Files created or modified
- `ingest/paths.py` — `workspace_key_for` + cursor/claude strategies
- `migrations/0006_workspace_key.sql`, `tests/test_schema_0006.py`, `fixtures/schema/0006_snapshot.json`
- `ingest/model.py`, `ingest/writer.py`, ingest golden + writer/orchestrator tests
- `dashboard/metrics.py` + `test_dashboard_metrics.py` (rollup by coalesce)
- `docs/architecture/warehouse.md`, `memory-bank/systemPatterns.md`
- Head pins: `test_migrate_runner.py`, `test_warehouse_open.py`, `test_warehouse_concurrency.py`

## Key implementation decisions
- Writer always derives via `workspace_key_for` at insert (does not trust pre-set model field)
- Cursor/Claude strategies share private leading-sep-stripped encode helper; registry remains the extension point
- Metrics `projects[]` = rollup keys; JS unchanged (already uses ids for hover titles)

## Deviations from plan
- Also bumped warehouse open/concurrency `_HEAD_VERSION` and locked snapshot to 0006 (preflight called out migrate_runner only)

## Integration test results
- Full suite pass; ingest golden regenerated with `workspace_key`

## Next Step
- QA review (automatic Level 3 transition)
