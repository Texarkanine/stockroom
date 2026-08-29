# Active Context

## Current Task: warehouse-schema-docs
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Implemented the 10-step `@rel` plan plus two QA reworks: visible Mermaid view aliases, then compact SKILL column-meaning guardrails the ERD cannot carry.
- 18 tests in `tests/test_warehouse_schema_docs.py`.

## Files created or modified
- Created: `scripts/gen_warehouse_schema.py`, `skills/sr-query/references/warehouse-schema.md`, `docs/advanced/warehouse-schema.md` (symlink), `skills/sr-search/tests/test_warehouse_schema_docs.py`
- Migrations (comments only): `0001_initial_schema.sql`, `0007_session_token_usage.sql`
- Wiring: `Makefile`, `.github/workflows/ci.yaml`, `docs/advanced/.pages`, `skills/sr-query/SKILL.md`, Advanced/Search/Architecture/contributing engine docs, `memory-bank/techContext.md`, `memory-bank/systemPatterns.md`
- QA rework 1: generator view aliases + regenerated ERD
- QA rework 2: `skills/sr-query/SKILL.md` compact meanings (project_id/cwd/workspace_key/entrypoint; thinking not captured; tool inputs only)

## Key implementation decisions
- `@rel` parser is stdlib regex; coverage runs inside `check()` / `write()`.
- Empty `primary_key` → Mermaid entity alias `name["name (view)"]`.
- SKILL keeps a short meaning note next to the ERD; no exhaustive catalog and no `as of migrations` pin.

## Deviations from the plan
- Ruff path from the engine cwd is `../../scripts`, not `../scripts`.
- First Build used `%% view:` (QA rejected); then the catalog deletion also dropped non-structural meanings (QA rejected). Both restored in rework.

## Integration test results
- Schema-docs tests: 18 passed. Skill hygiene: run after SKILL.md rework.
- Earlier `make test` with Node 22: JS 134 passed; engine 856 passed, 5 skipped, 1 pre-existing `/tmp` identity fail.

## Next Step
- QA passed. Proceed to `/niko-reflect`.
