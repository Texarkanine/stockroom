# Task: fix-pr152-check-blockers

* Task ID: fix-pr152-check-blockers
* Complexity: Level 2
* Type: bug fix

Two prescribed corrections on pull request 152. Session start must run `stockroom.check` with the engine `.venv` interpreter, which has `duckdb`. `copy_warehouse` must accept a warehouse DuckDB 1.5.4 wrote, whose `sessions` default is still `CAST('f' AS BOOLEAN)` after migration to schema 9.


## Test Plan (TDD)

### Behaviors to Verify

- Cursor session start: the `sessionStart` command contains `PYTHONPATH="$APP/src" "$APP/.venv/bin/python" -m stockroom.check` after `stockroom dashboard`, which is after `shim rectify`.
- Claude session start: the `SessionStart` command contains that same check token, in that same order.
- Both session-start commands: the check is not `PYTHONPATH="$APP/src" "$PY" -m stockroom.check`.
- Both session-start commands: rectify is still `PYTHONPATH="$APP/src" "$PY" -m stockroom shim rectify`.
- Cursor `beforeSubmitPrompt`: the command still does not contain `stockroom.check`. Existing test, unchanged.
- DuckDB 1.5.4 origin: `released_chain_154(8)` placed at the warehouse path, then `warehouse.open(read_only=False)` closed, leaves schema version 9 and `CAST('f' AS BOOLEAN)` in the `sessions` table SQL.
- That file: `storage.copy_warehouse` returns a sibling and does not raise.
- That sibling: its `sessions` table SQL contains `DEFAULT(false)` and is not equal to the original `sessions` table SQL.
- Edge, unchanged: `generations_file` copy still matches zstd-stripped table SQL in `test_copy_warehouse_catalog_matches_when_each_file_is_alone`. That fixture is written by DuckDB 2.0.0, so the strings match. Do not delete that assert.
- Edge, unchanged: `test_schema_file_matches_chain_at_nine` still compares zstd-stripped table SQL between the schema file and the released chain at 9, both `v2.0.0`.
- Edge, unchanged: `test_verify_copy_rejects_a_deleted_row` still raises `CopyMismatch`.
- Edge, unchanged: a schema-8 file that was not migrated still raises `CopyError` from `copy_warehouse`.
- Stop condition: if the new copy raises `CopyMismatch` and the message names a part other than `table_sql`, stop. Do not drop another catalog part.

### Test Infrastructure

- Framework: pytest, configured in `skills/sr-search/pyproject.toml`
- Test location: `skills/sr-search/tests/`
- Conventions: one behavior per test, docstring states the behavior, fixtures from `conftest.py` (`cursor_hooks`, `claude_hooks`, `warehouse_home`, `released_chain_154`)
- New test files: none

## Implementation Plan

### 1. Session-start check interpreter — executable [x]

- Files: `skills/sr-search/tests/test_packaging.py`, `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`
- Do not change `skills/sr-search/src/stockroom/check.py`. `launch` already spawns `sys.executable`. The hook parent must be the `.venv` interpreter, or `import duckdb` fails before `launch`.
- Do not change the `;` between rectify, the dashboard, and the check. Rectify stays on `"$PY"`. `beforeSubmitPrompt` stays without a check.

1. Stub tests: In `test_packaging.py`, add `test_session_start_check_uses_the_engine_venv(cursor_hooks, claude_hooks)` with a docstring and an empty body. Leave `_assert_detached_check` as it is for this stub.
2. Stub interface: No new Python function. The interface is the check token in the two hook commands. Do not edit the JSON in this substep.
3. Write tests and run red: Set `_assert_detached_check`'s token to `PYTHONPATH="$APP/src" "$APP/.venv/bin/python" -m stockroom.check` and keep the order assert (`check` after `stockroom dashboard` after `shim rectify`). Implement `test_session_start_check_uses_the_engine_venv` so each of the Cursor `sessionStart` command and the Claude `SessionStart` command contains that token, does not contain `PYTHONPATH="$APP/src" "$PY" -m stockroom.check`, and still contains `"$PY" -m stockroom shim rectify`. Run:

```
uv --directory skills/sr-search --no-config run --no-sync pytest -n0 skills/sr-search/tests/test_packaging.py::test_cursor_hook_schema_and_combined_command skills/sr-search/tests/test_packaging.py::test_claude_hook_schema_and_combined_command skills/sr-search/tests/test_packaging.py::test_session_start_check_uses_the_engine_venv skills/sr-search/tests/test_packaging.py::test_cursor_beforesubmit_path_only_suspenders
```

The three session-start tests fail while the hooks still use `"$PY"` for the check. `test_cursor_beforesubmit_path_only_suspenders` stays green.

4. Write code and run green: In both hook commands, replace only `PYTHONPATH="$APP/src" "$PY" -m stockroom.check` with `PYTHONPATH="$APP/src" "$APP/.venv/bin/python" -m stockroom.check`. Run the same pytest command. All four tests pass.

### 2. Lifecycle sentence — prose/policy [x]

- Files: `docs/architecture/lifecycle.md`
- No tests: prose/policy artifact
- This is the only tracked document that names `"$PY" -m stockroom.check`. `memory-bank/systemPatterns.md` says the check is `python -m stockroom.check` and that rectify uses `uv python find`. Both of those sentences stay true. Do not edit them.

1. Replace session-start item 3 with this sentence, and leave items 1 and 2 as they are:

`3. **The check** — `"$APP/.venv/bin/python" -m stockroom.check` on the engine `.venv` interpreter that rectify just ensured. The child is detached. The hook does not wait for the check. The check is not an on-path `stockroom` command.`

### 3. Drop table SQL from the catalog compare — executable [x]

- Files: `skills/sr-search/tests/test_storage.py`, `skills/sr-search/src/stockroom/storage.py`
- Do not change `test_schema_file_matches_chain_at_nine` or `test_copy_warehouse_catalog_matches_when_each_file_is_alone`.
- Do not change released migration SQL.

1. Stub tests: Add `test_copy_warehouse_accepts_a_154_origin_boolean_default(warehouse_home, released_chain_154)` in `test_storage.py` with this docstring and an empty body:

```
A warehouse DuckDB 1.5.4 wrote still copies after warehouse.open migrates it to schema 9.

The migrated sessions default is still CAST('f' AS BOOLEAN). The schema-file sibling spells that default as DEFAULT(false). copy_warehouse returns the sibling.
```

2. Stub interface: No new function and no signature change. `_catalog` loses a key in substep 4. Do not edit `storage.py` in this substep.

3. Write tests and run red: Implement the test. Under `warehouse_home`, copy `released_chain_154(8)` onto `warehouse.warehouse_path()`, call `warehouse.open(read_only=False)` and close it, then read `sessions` SQL from that file. Assert schema version 9 and that the SQL contains `CAST('f' AS BOOLEAN)`. Call `storage.copy_warehouse` on that path. Assert it returns a sibling whose `sessions` SQL contains `DEFAULT(false)` and is not equal to the original `sessions` SQL. Use the same `duckdb_tables()` read as `_tables_sql`. Run:

```
uv --directory skills/sr-search --no-config run --no-sync pytest -n0 skills/sr-search/tests/test_storage.py::test_copy_warehouse_accepts_a_154_origin_boolean_default
```

Expected red: `storage.CopyMismatch` with message `table_sql differ from the original`. If the message names another part, stop and do not edit `_catalog`. If `CAST('f' AS BOOLEAN)` is absent after the open, stop and do not weaken the assert.

4. Write code and run green: In `_catalog`, delete the `duckdb_tables()` query and the `table_sql` key. Replace the `verify_copy` docstring sentences that mention table SQL with: `Compares columns, constraints, indexes, the view name, and view columns by opening each file with nothing attached. Does not compare table SQL or view SQL.` Leave the `EXCEPT ALL` and zstd sentences. Replace the `_catalog` docstring with: `Schema facts that must match. Table SQL is not one of them.` Run the new test, then:

```
uv --directory skills/sr-search --no-config run --no-sync pytest -n0 skills/sr-search/tests/test_storage.py::test_copy_warehouse_accepts_a_154_origin_boolean_default skills/sr-search/tests/test_storage.py::test_copy_warehouse_catalog_matches_when_each_file_is_alone skills/sr-search/tests/test_storage.py::test_schema_file_matches_chain_at_nine skills/sr-search/tests/test_storage.py::test_verify_copy_rejects_a_deleted_row
```

All four pass. The whole engine suite runs at the end of build, not in this plan step.

## Technology Validation

No new technology - validation not required. The 1.5.4 warehouse comes from the existing `released_chain_154` fixture (`uv run --with duckdb==1.5.4`).

## Dependencies

- `uv` on PATH, already required by `released_chain_154`
- Engine venv with the locked DuckDB, already required by pytest
- Pull request 152 branch `warehouse-file-growth`

## Challenges & Mitigations

- The hook uses `;`, so the check runs even when rectify fails and `.venv` is missing. The failure stays inside `|| true`. Do not change that control flow.
- `check.launch` uses `sys.executable`. Changing only `launch` would not help: the bare interpreter raises `ModuleNotFoundError` on `import duckdb` before `launch`. The hook command is the process that imports `stockroom.check`.
- A 1.5.4 catalog may differ in a part other than `table_sql`. The red run must report `table_sql differ from the original`. Another part stops the build.
- `warehouse.open` is the migration path already proven on `released_chain_154` files. Do not open that file and `CHECKPOINT` it before version 9.
- The commit hook's frozen sync removes torch. These tests do not import torch. Use `--no-sync` so a later sync is not required for this plan.

## Pre-Mortem

- The plan fixes the child command and leaves the parent on the bare interpreter. The parent is the process that runs `-m stockroom.check` and imports `duckdb`. Substep 4 of step 1 changes that parent. `launch` stays. Already covered by Challenge 2.
- Dropping `table_sql` hides a real column or constraint drift, and the check swaps a wrong schema. The remaining `_catalog` keys and `_require_zstd` stay. `test_schema_file_matches_chain_at_nine` still pins table SQL for two `v2.0.0` files. The new test requires the 1.5.4 spelling and the sibling spelling to differ, so a silent normalization is visible. A red message other than `table_sql` stops the build rather than dropping more keys.
- Migration to schema 9 rewrites the boolean default, the precondition assert fails, and someone deletes it to get a green copy. The plan says stop when `CAST('f' AS BOOLEAN)` is absent. Do not delete that assert.
- `test_copy_warehouse_catalog_matches_when_each_file_is_alone` is treated as coverage of this bug. It uses `generations_file`, which DuckDB 2.0.0 writes, so both sides spell `DEFAULT(false)`. The new test is the 1.5.4-origin copy. The old assert stays.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
