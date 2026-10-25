# Progress

Fix the two pull request 152 release blockers on `warehouse-file-growth`: run the session-start warehouse check with the engine `.venv` interpreter, and stop treating DuckDB 1.5.4 boolean-default spelling as a catalog mismatch.

**Complexity:** Level 2

## 2026-10-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed intent against `.scratch/issue-1-hook-python-check.md` and `.scratch/issue-2-table-sql-mismatch.md`
    - Confirmed the open pull request is 152 on `warehouse-file-growth`
    - Wrote the project brief
* Decisions made
    - Level 2: two prescribed bug fixes across the hook command and the catalog compare, with no open design choice
* Insights
    - Each fix is isolated, and together they touch two components, so the task is not a single-component Level 1 fix

## 2026-10-25 - PLAN - COMPLETE

* Work completed
    - Surveyed the hook commands, `check.launch`, `_catalog`, and the copy tests
    - Wrote the Level 2 plan in `tasks.md`
* Decisions made
    - The hook parent must be `$APP/.venv/bin/python`, because that process imports `duckdb` before `launch`
    - `table_sql` leaves `_catalog`. Table SQL between two `v2.0.0` files stays pinned by `test_schema_file_matches_chain_at_nine`
    - The 1.5.4 copy test migrates with `warehouse.open`, the path already used for those files
* Insights
    - `generations_file` is written by DuckDB 2.0.0, so its table SQL matches a schema-file copy and cannot catch this bug
    - `docs/architecture/lifecycle.md` is the only tracked page that names `"$PY" -m stockroom.check`

## 2026-10-25 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the Level 2 plan against the codebase: hook commands, packaging tests, `_catalog`, fixtures, and lifecycle docs all match the plan's claims
    - Wrote `memory-bank/active/.preflight-status` with first line `PASS WITH ADVISORY`
* Decisions made
    - No plan edits needed: TDD ordering is correct in both executable units, the prose unit correctly owes no tests, and no change-detectors were scheduled
    - Recorded one advisory: routing the check through a `stockroom check --detach` shim subcommand would give the interpreter question one owner, at the cost of reversing an archived decision
* Insights
    - `_catalog` is private to `storage.py` and the copy tests use their own helpers, so dropping `table_sql` breaks nothing unlisted
    - The expected red message `table_sql differ from the original` matches `_verify_catalog`'s f-string exactly

## 2026-10-25 - BUILD - COMPLETE

* Work completed
    - Session-start hooks and packaging tests now run the check with `$APP/.venv/bin/python`
    - Lifecycle item 3 names that interpreter
    - `copy_warehouse` accepts a DuckDB 1.5.4-origin warehouse at schema 9
    - `make ci`: 1167 pytest passed, 39 skipped; 134 dashboard JavaScript tests passed
* Decisions made
    - Left `check.launch` on `sys.executable`, because the hook parent is now the `.venv` interpreter
    - Did not add a `stockroom check` subcommand. The preflight advisory stays out of this build
* Insights
    - The red copy failed with `table_sql differ from the original` after migration left `CAST('f' AS BOOLEAN)` in place
    - `uv --directory` runs pytest with the engine directory as cwd, so the plan's `skills/sr-search/tests/...` paths do not resolve
