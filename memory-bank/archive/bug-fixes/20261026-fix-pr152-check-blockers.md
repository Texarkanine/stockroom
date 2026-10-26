---
task_id: fix-pr152-check-blockers
complexity_level: 2
date: 2026-10-26
status: completed
---

# TASK ARCHIVE: Fix PR 152 check blockers

## SUMMARY

Fixed the two release blockers on pull request 152. Session start runs `stockroom.check` with `$APP/.venv/bin/python`, the interpreter that has DuckDB. `copy_warehouse` accepts a warehouse DuckDB 1.5.4 wrote, whose `sessions` default is still `CAST('f' AS BOOLEAN)` after migration to schema 9. QA passed on the first review.

## REQUIREMENTS

1. Both session-start hooks run `PYTHONPATH="$APP/src" "$APP/.venv/bin/python" -m stockroom.check`.
2. The packaging tests fail if that invocation returns to `"$PY"`. Rectify stays on `"$PY"`. `beforeSubmitPrompt` does not start the check.
3. `docs/architecture/lifecycle.md` names the engine `.venv` interpreter for the check.
4. `_catalog` drops `table_sql`. Columns, constraints, indexes, views, view columns, and the zstd check stay.
5. A `released_chain_154(8)` warehouse migrated to schema 9 copies successfully, and its `sessions` SQL still contains `CAST('f' AS BOOLEAN)` while the sibling contains `DEFAULT(false)`.
6. `test_schema_file_matches_chain_at_nine` still pins table SQL between two `v2.0.0` files. Released migration SQL stays unchanged.

The preflight sketch of a `stockroom check` subcommand stayed out of the build.

## IMPLEMENTATION

- `hooks/cursor-hooks.json` and `hooks/claude-hooks.json`: only the check token changed. The `;` between rectify, the dashboard, and the check stayed. Rectify still uses `uv python find`.
- `skills/sr-search/src/stockroom/check.py`: unchanged. `launch` still spawns `sys.executable`. The hook parent is now the `.venv` interpreter, so that child is too.
- `docs/architecture/lifecycle.md`: session-start item 3 names `"$APP/.venv/bin/python" -m stockroom.check` on the engine `.venv` interpreter that rectify just ensured.
- `skills/sr-search/src/stockroom/storage.py`: `_catalog` no longer reads `duckdb_tables()` SQL. `verify_copy` says it does not compare table SQL or view SQL.
- `memory-bank/systemPatterns.md`: the check runs on `$APP/.venv/bin/python` after rectify, not on the bare interpreter.

The red copy failed with `table_sql differ from the original` after `warehouse.open` left `CAST('f' AS BOOLEAN)` in place. No other catalog part differed, so nothing else was dropped.

## TESTING

`test_session_start_check_uses_the_engine_venv` and the updated `_assert_detached_check` went red on `"$PY"`, then green. `test_copy_warehouse_accepts_a_154_origin_boolean_default` went red on `table_sql differ from the original`, then green. The `v2.0.0` table-SQL pin, the alone-file catalog match, and the deleted-row rejection stayed green.

`make ci` passed: 1167 pytest tests, 39 skipped, and 134 dashboard JavaScript tests. QA passed on the first review and reran the eight targeted tests. QA noted that a default-only wording change is no longer a catalog mismatch. That is the trade-off the brief asked for. The surviving catalog keys, the row compare, the zstd check, and the `v2.0.0` table-SQL pin bound it.

## LESSONS LEARNED

- DuckDB 2.0.0 does not rewrite a DuckDB 1.5.4 boolean default during migration to schema 9. `generations_file` cannot catch that, because DuckDB 2.0.0 writes `DEFAULT(false)` even into a `v1.0.0` file.
- The process that runs `python -m stockroom.check` imports DuckDB before `launch` spawns a child. The hook parent has to be the `.venv` interpreter. Changing only `launch` would not help.

## PROCESS IMPROVEMENTS

Name the expected red message in the plan. The copy test was allowed to stop the build if the mismatch named any part other than `table_sql`, which kept the edit to the one prescribed key.

Pytest under `uv --directory skills/sr-search` uses engine-relative paths. A plan written from the repo root as `skills/sr-search/tests/...` does not resolve.

## TECHNICAL IMPROVEMENTS

Compare columns, constraints, indexes, views, and storage, and do not compare table SQL that two DuckDB writers spell differently. A `stockroom check` shim command would give the interpreter one owner, the way the dashboard already does. That reverses the decision that the check is not a `stockroom` subcommand, so this build kept the hook token.

## NEXT STEPS

None for this fix. The shim-subcommand sketch stays an advisory.
