# Active Context

## Current Task: warehouse-schema-docs
**Phase:** PLAN - COMPLETE

## What Was Done
- Operator asked to fold in preflight's `@rel` radical innovation. Plan now: edges live as `-- @rel` / `-- @rel-none` comments in migration SQL; coverage fails if a head-snapshot entity is undeclared; goldens still supply boxes/columns; no dummy DuckDB.
- Prior preflight fixes kept: ruff `../scripts`, link-free generated body, `.pages` nav with the symlink, engine.md documents the regen loop (now including `@rel`).

## Next Step
- Re-run Preflight on the `@rel`-expanded plan
