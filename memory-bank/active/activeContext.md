# Active Context

## Current Task: warehouse-schema-docs
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented the 10-step `@rel` plan: stdlib generator, migration comments, committed ERD SSOT, docs symlink, Make/CI lockstep, skill + human docs routing, contributor loop, memory-bank pointers.
- QA FAIL (fixable) rework: empty-PK entities now use a visible Mermaid entity alias instead of a non-rendered `%%` comment.
- 18 tests in `tests/test_warehouse_schema_docs.py` (toy render, visible view alias, parser, coverage, lockstep, symlink, Make pin).

## Files created or modified
- Created: `scripts/gen_warehouse_schema.py`, `skills/sr-query/references/warehouse-schema.md`, `docs/advanced/warehouse-schema.md` (symlink), `skills/sr-search/tests/test_warehouse_schema_docs.py`
- Migrations (comments only): `0001_initial_schema.sql`, `0007_session_token_usage.sql`
- Wiring: `Makefile`, `.github/workflows/ci.yaml`, `docs/advanced/.pages`, `skills/sr-query/SKILL.md`, Advanced/Search/Architecture/contributing engine docs, `memory-bank/techContext.md`, `memory-bank/systemPatterns.md`
- QA rework: `scripts/gen_warehouse_schema.py`, `tests/test_warehouse_schema_docs.py`, regenerated `skills/sr-query/references/warehouse-schema.md`

## Key implementation decisions
- `@rel` parser is stdlib regex; coverage runs inside `check()` / `write()`.
- Empty `primary_key` → Mermaid entity alias `name["name (view)"]` (box title); relationship lines keep the SQL name.
- DuckDB types `FLOAT[384]` / `VARCHAR[]` sanitize to `FLOAT_384` / `VARCHAR_ARRAY`.

## Deviations from the plan
- Ruff path from the engine cwd is `../../scripts`, not `../scripts` (that resolves to `skills/scripts`). Makefile and CI use the corrected path.
- `assert_coverage` reports missing `@rel` columns before unaccounted snapshot names, so a typo’d column is visible even on a partial rel set.
- The importlib test fixture registers the generator in `sys.modules` so dataclasses load under Python 3.14.
- First Build used `%% view:` which QA rejected as non-rendered; rework uses official ERD aliases.

## Integration test results
- `tests/test_warehouse_schema_docs.py`: 18 passed.
- `make test` with Node 22: dashboard JS 134 passed; engine pytest 856 passed, 5 skipped, 1 pre-existing fail (`test_dashboard_identity` `/tmp` vs `/private/tmp` on macOS). None are in the schema-docs files.
- `make lint`, `make format-check`, `make schema-docs-check`, `make reuse`, `make docs-build`: passed.

## Next Step
- QA review (`/niko-qa`) runs automatically.
