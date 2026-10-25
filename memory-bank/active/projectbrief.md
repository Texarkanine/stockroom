# Project Brief

## User Story

As a Stockroom user taking the next release, I want the session-start warehouse check to run on an interpreter that has DuckDB, and I want a warehouse created under DuckDB 1.5.4 to pass the copy check, so the zstd swap on pull request 152 can finish.

## Use-Case(s)

### Use-Case 1

Session start runs `shim rectify`, which ensures the engine environment, then starts `stockroom.check`. The check must use `$APP/.venv/bin/python`, the interpreter that has `duckdb`. The bare `uv python find` interpreter does not.

### Use-Case 2

The check copies a warehouse that began on DuckDB 1.5.4. That file's `sessions` table SQL still says `DEFAULT(CAST('f' AS BOOLEAN))`. A new copy built from the frozen schema says `DEFAULT(false)`. That spelling difference must not fail the copy or stop the check.

## Requirements

1. In `hooks/cursor-hooks.json` and `hooks/claude-hooks.json`, replace `PYTHONPATH="$APP/src" "$PY" -m stockroom.check` with `PYTHONPATH="$APP/src" "$APP/.venv/bin/python" -m stockroom.check`, as specified in `.scratch/issue-1-hook-python-check.md`.
2. In `skills/sr-search/tests/test_packaging.py`, update `_assert_detached_check` to that `.venv` invocation, and add a test that the session-start check runs under the project `.venv` interpreter rather than the bare `uv python find` interpreter.
3. In `docs/architecture/lifecycle.md`, change session-start item 3 so the check is `"$APP/.venv/bin/python" -m stockroom.check`, the engine `.venv` interpreter that rectify just ensured.
4. In `skills/sr-search/src/stockroom/storage.py`, remove `table_sql` from `_catalog`, and update the `verify_copy` and `_catalog` docstrings, as specified in `.scratch/issue-2-table-sql-mismatch.md`.
5. Add a test that copies a `released_chain_154(8)` warehouse migrated to version 9, so a real DuckDB 1.5.4-origin catalog is covered by `copy_warehouse`.
6. Keep `test_schema_file_matches_chain_at_nine` as the `table_sql` pin between two `v2.0.0` files. Update `test_copy_warehouse_catalog_matches_when_each_file_is_alone` only if it must follow `_catalog`.

## Constraints

1. Land the work on the open pull request 152 branch `warehouse-file-growth`.
2. The scratch notes are the fix. Do not widen the check state machine or the hook events.
3. `shim rectify` stays on the bare `uv python find` interpreter. `beforeSubmitPrompt` does not start the check.
4. Structural equivalence stays on `columns`, `constraints`, `indexes`, `views`, `view_columns`, and `_require_zstd`.
5. Released migration SQL stays unchanged.

## Acceptance Criteria

1. Both session-start hooks invoke the check with `"$APP/.venv/bin/python"`, and the packaging test fails if that invocation returns to `"$PY"`.
2. `docs/architecture/lifecycle.md` names that same interpreter for the check.
3. `copy_warehouse` accepts a DuckDB 1.5.4-origin warehouse whose `table_sql` spells the boolean default as `CAST('f' AS BOOLEAN)`.
4. A real schema mismatch that the remaining catalog checks can see still fails the copy.
5. `test_schema_file_matches_chain_at_nine` still locks table SQL for two `v2.0.0` files.
