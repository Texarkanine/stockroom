# Active Context

## Current Task: Token Usage Grain & Rollups
**Phase:** BUILD - COMPLETE

## What Was Done
- Migration `0007_session_token_usage.sql`: four nullable `sessions.*_tokens` + VIEW `session_token_usage`
- Schema contract + golden `0007_snapshot.json`; VIEW locked via `duckdb_views()` + seeded semantics
- `NormalizedSession` + writer persist session tokens when set; leave NULL when unset (no invent from message sums)
- Docs: warehouse dual-grain doctrine, search rollup example, `sr-search`/`sr-query` SKILL guidance
- Head-version pins bumped to 7 (`test_migrate_runner`, `test_warehouse_open`, `test_warehouse_concurrency`)
- Verification: format/lint clean; full suite 617 passed, 4 skipped

## Next Step
- QA review runs next (`/niko-qa` via Level 3 phase transition)
