# Active Context

## Current Task: advanced-usage-docs
**Phase:** BUILD - COMPLETE

## What Was Done
- Stubbed `docs/advanced/{index,cli,duckdb}.md` + `.pages` (Overview → CLI → DuckDB)
- Rewrote landing (audience / is / isn’t / TOC)
- Rewrote CLI as OOB shim + query/semantic depth; other subcommands are link-outs only
- Added DuckDB RO page (`duckdb -readonly` → `$STOCKROOM_HOME/warehouse.duckdb`)
- Retargeted Architecture warehouse escape-hatch + change-surfaces; normalized UG Advanced link text
- `make docs-build` PASS (strict)
- Persistent MB: no change needed (no Advanced ownership sentences)

## Deviations
- None — built to plan (home DuckDB caption advisory still deferred)

## Next Step
- `/niko-qa` (automatic for L3 after Build PASS)
