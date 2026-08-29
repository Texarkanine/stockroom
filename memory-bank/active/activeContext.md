# Active Context

## Current Task: warehouse-schema-docs
**Phase:** PLAN - COMPLETE

## What Was Done
- Level 3 plan written: generate a Mermaid ERD from the existing head schema golden snapshot (`0008_snapshot.json` today) via a stdlib `scripts/gen_warehouse_schema.py`, commit SSOT at `skills/sr-query/references/warehouse-schema.md`, expose it in Advanced via cookbook-style symlink, CI/`make schema-docs-check` fails on drift.
- Dummy DuckDB generation rejected: goldens already lock migrated schema; operator preferred a lighter technique.
- No creative phase — approach is determined by existing goldens + cookbook dual-audience pattern + stated constraints.

## Next Step
- Preflight: spawn `/niko-preflight` subagent to validate the plan against the codebase
