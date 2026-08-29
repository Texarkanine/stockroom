# Active Context

## Current Task: warehouse-schema-docs
**Phase:** PLAN - COMPLETE

## What Was Done
- Folded `@rel` into the plan; third preflight FAIL (fixable): CI ruff steps bypass Make and would miss `scripts/gen_warehouse_schema.py`.
- Re-planned: engine-job Lint / Format check also `ruff … . ../scripts`. Makefile change remains for local `make lint`.

## Next Step
- Re-run Preflight
