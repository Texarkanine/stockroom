# Active Context

## Current Task: fix-plugin-env-heal-after-move
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented `stockroom.engine_env.ensure_engine_env` (inexact `--check` / `--inexact` heal).
- Wired into `shim rectify` + `shim ensure-env` CLI; hooks use stdlib `python3` bootstrap, timeout 60, Claude PATH parity.
- Shim template refuses when duckdb not importable; docs/`sr-initialize`/`system-model` updated.
- Verification: 435 passed, 3 skipped; lint clean; live empty-venv → ensure-env → duckdb_ok.

## Files modified
- `skills/sr-search/src/stockroom/engine_env.py` (new)
- `skills/sr-search/src/stockroom/shim.py`, `shim_template.sh`
- `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`
- `skills/sr-initialize/SKILL.md`, `docs/development.md`, `skills/sr-search/references/system-model.md`
- Tests: `test_engine_env.py` (new), `test_shim*.py`, `test_packaging.py`

## Next Step
- QA phase.
