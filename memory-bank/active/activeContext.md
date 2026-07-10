# Active Context

## Current Task: xdg-base-directory-layout
**Phase:** BUILD - COMPLETE

## What Was Done
- `warehouse.resolve_home()` + XDG/`STOCKROOM_HOME` `home_dir()`; doctor `home` / `home-source`
- Living docs + O1/D7 + spike paths reconciled; no legacy migration
- Full `make test` + lint green

## Files
- `skills/sr-search/src/stockroom/warehouse.py`, `doctor.py`, `schedule.py` (doc)
- `skills/sr-search/tests/test_warehouse_home_xdg.py`, `test_doctor*.py`, `conftest.py`, `test_warehouse_open.py`
- `memory-bank/{systemPatterns,techContext}.md`, planning brainstorm/tech-brief/spike

## Deviations
- None beyond preflight advisory (pure `resolve_home` for doctor)

## Next Step
- `/niko-qa`
