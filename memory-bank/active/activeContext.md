# Active Context

## Current Task: fix-session-start-heal-after-plugin-move
**Phase:** BUILD - COMPLETE

## What Was Done
- Extracted XDG/`STOCKROOM_HOME` resolution to `skills/sr-search/src/stockroom/home.py` (stdlib-only)
- `warehouse.py` re-exports home names; `torch_source.py` imports `home_dir` from `stockroom.home`
- Added `tests/test_shim_import_graph.py` (3 subprocess pins); full suite 470 passed, 3 skipped; ruff clean
- Surgical `systemPatterns.md` note on DuckDB-free heal imports; hooks unchanged

## Next Step
- QA review (automatic)
