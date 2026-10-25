# Active Context

## Current Task: fix-pr152-check-blockers
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Modified `/home/mobaxterm/git/stockroom/hooks/cursor-hooks.json`
- Modified `/home/mobaxterm/git/stockroom/hooks/claude-hooks.json`
- Modified `/home/mobaxterm/git/stockroom/docs/architecture/lifecycle.md`
- Modified `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_packaging.py`
- Modified `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_storage.py`
- Modified `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/storage.py`
- Session start runs the check with `$APP/.venv/bin/python`. Rectify still uses `"$PY"`. `check.launch` is unchanged
- `_catalog` no longer returns `table_sql`. Columns, constraints, indexes, views, view columns, and the zstd check remain
- The new copy test migrated a DuckDB 1.5.4 schema-8 warehouse with `warehouse.open`, saw `CAST('f' AS BOOLEAN)`, and failed on `table_sql differ from the original` before the compare was removed
- Deviation: pytest was invoked as `tests/...` under the engine directory. `uv --directory` does not keep the repo-root paths the plan wrote

## Next Step
- `/niko-reflect`
