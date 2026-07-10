# Active Context

## Current Task: fix-session-start-heal-after-plugin-move
**Phase:** PLAN - COMPLETE

## What Was Done
- Level 2 plan written for [issue #25](https://github.com/Texarkanine/stockroom/issues/25)
- Root cause confirmed: `shim` → `engine_env` → `torch_source` → `warehouse` → `import duckdb` dies on bare `uv python find` before `ensure_engine_env`
- Approach: extract XDG/`STOCKROOM_HOME` resolution to dep-light `stockroom.home`; point `torch_source` at it; warehouse re-exports; pin with subprocess import-graph test; leave hook JSON thin/unchanged

## Next Step
- Preflight validation (automatic)
