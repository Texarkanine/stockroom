# Task: fix-session-start-heal-after-plugin-move

* Task ID: fix-session-start-heal-after-plugin-move
* Complexity: Level 2
* Type: bug fix

After a marketplace plugin-hash move, session-start hooks die importing `stockroom.shim` with `ModuleNotFoundError: No module named 'duckdb'` before `ensure_engine_env` can sync the new tree ([issue #25](https://github.com/Texarkanine/stockroom/issues/25)). Break the heal import graph so `torch_source` no longer pulls `warehouse` (and thus DuckDB) at module load; keep thin hooks; Python remains the single heal owner.

## Test Plan (TDD)

### Behaviors to Verify

- [B1 — shim import is duckdb-free]: In a clean subprocess, (a) `import stockroom.shim` succeeds with `duckdb` absent from `sys.modules`, and (b) `python -m stockroom shim --help` exits 0 without importing duckdb → heal entrypoint can start on a bare `uv python find` interpreter
- [B2 — home resolution still works after extract]: `resolve_home` / `home_dir` prefer `STOCKROOM_HOME`, then `$XDG_DATA_HOME/stockroom`, else `~/.local/share/stockroom`; `home_dir` mkdir; `resolve_home` does not → same contract as today (via new module and warehouse re-exports)
- [B3 — torch_source uses light home]: `torch_source.index_path` / `requirements_path` resolve under stockroom home without importing `warehouse` / `duckdb` at module load
- [B4 — ensure_engine_env still callable after light imports]: Importing `engine_env` / calling `ensure_engine_env` with injectable runner still syncs then ensures torch (existing suite must keep passing)
- [B5 — hooks stay thin / no empty-venv footgun]: Cursor `sessionStart` and Claude `SessionStart` still bootstrap via `uv python find` + `"$PY" -m stockroom shim rectify` (no `uv run --no-sync` in rectify half) → packaging contract unchanged
- [Edge — warehouse public home API]: Existing callers/`test_warehouse_home_xdg.py` still see `warehouse.home_dir` / `resolve_home` / constants (re-exports)
- [Edge — freeze missing soft-fail]: Existing `ensure_torch` soft-fail when freeze absent must not regress (covered by `test_torch_source.py`)

### Test Infrastructure

- Framework: pytest (configured in `skills/sr-search/pyproject.toml`); run via root `Makefile` (`make test`)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_<area>.py`; module docstring describing contract; injectable runners for uv; subprocess for CLI/runtime isolation; fixtures in `conftest.py` where shared
- New test files: `skills/sr-search/tests/test_shim_import_graph.py` (B1); optionally `test_home.py` if home tests move with the extract — prefer keeping `test_warehouse_home_xdg.py` pointed at warehouse re-exports and adding a thin import-graph assertion for `stockroom.home` / `torch_source` in the new file or `test_torch_source.py`

## Implementation Plan

1. **Failing pin: shim import / dispatcher path must not load duckdb**
   - Files: `skills/sr-search/tests/test_shim_import_graph.py` (new)
   - Changes: Subprocess with `PYTHONPATH` to `src` (a) imports `stockroom.shim` and asserts `'duckdb' not in sys.modules`; (b) runs `python -m stockroom shim --help` and asserts exit 0 with no duckdb import (same `sys.modules` probe via `-c` wrapper or env). Expect fail on current graph.

2. **Failing/relocated home + torch_source import pins (as needed)**
   - Files: `skills/sr-search/tests/test_shim_import_graph.py` and/or `test_torch_source.py`
   - Changes: Assert `import stockroom.torch_source` does not load `duckdb`; keep XDG behaviors green via warehouse re-exports after step 3.

3. **Extract dep-light home resolution**
   - Files: `skills/sr-search/src/stockroom/home.py` (new); `skills/sr-search/src/stockroom/warehouse.py`
   - Changes: Move `HOME_ENV_VAR`, `XDG_DATA_HOME_ENV_VAR`, `HOME_SOURCE_*`, `resolve_home()`, `home_dir()` into `stockroom.home` (stdlib only). `warehouse` re-exports those names for existing callers/tests. Leave `import duckdb` and DuckDB open path in `warehouse`.

4. **Point heal stack at light home**
   - Files: `skills/sr-search/src/stockroom/torch_source.py`
   - Changes: Replace `from stockroom.warehouse import home_dir` with `from stockroom.home import home_dir`. Confirm import chain: `shim` → `engine_env` → `torch_source` → `home` (no `warehouse`/`duckdb`).

5. **Re-run targeted then full verification**
   - Files: none (verification)
   - Changes: Run new import-graph tests + `test_warehouse_home_xdg.py`, `test_torch_source.py`, `test_engine_env.py`, `test_shim*.py`, `test_packaging.py`; then full `make test` / lint/format as required by build.

6. **Docs / patterns only if factually wrong**
   - Files: `docs/development.md` and/or `memory-bank/systemPatterns.md` (surgical only)
   - Changes: If heal description still implies warehouse-coupled imports, add one line that heal/home resolution is DuckDB-free. No hook JSON changes unless a test proves the bootstrap string must change (expected: unchanged).

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing: `stockroom.shim.rectify` → `ensure_engine_env` → `ensure_torch` (heal logic already correct when reachable)
- Existing: packaging hook tests in `test_packaging.py` pin bootstrap shape
- Prior art: [#17](https://github.com/Texarkanine/stockroom/issues/17) env heal; [#23](https://github.com/Texarkanine/stockroom/issues/23) `uv python find` bootstrap (regression surface)

## Challenges & Mitigations

- **Challenge: in-process `sys.modules` checks are polluted by other tests**: Mitigate with a dedicated subprocess (same pattern as `test_shim_cli.py` / `test_shim_runtime.py`).
- **Challenge: warehouse re-export drift / circular imports**: Keep `home` stdlib-only; warehouse imports home; never home→warehouse. Re-export explicitly in warehouse module namespace.
- **Challenge: temptation to shell-sync in hooks**: Rejected by issue preferred direction and empty-venv footgun; packaging tests already forbid `uv run` in rectify half — leave hooks alone.
- **Challenge: acceptance “delete .venv + dead hash” is integration-shaped**: Unit pin proves import reachability; existing ensure/torch tests prove heal once imported; optional manual smoke after build if operator wants live plugin-cache confirmation.

## Pre-Mortem

- **Plan “fixed” imports but heal still fails because something else in the `-m stockroom` path imports duckdb before shim**: Dispatcher already lazy-imports subcommands; pin the test on `import stockroom.shim` *and* a subprocess `python -m stockroom shim --help` / rectify dry path if needed. If `__main__` or package init ever gains eager warehouse imports, extend the pin.
- **Extracted `home` but left a second copy of XDG logic that drifts**: Already covered by Challenge (re-export + single owner in `stockroom.home`).
- **Chose shell sync in hooks under time pressure and reintroduced empty `.venv`**: Already covered by Challenge (hooks unchanged; packaging asserts).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA

## QA Results

- PASS: KISS/DRY/YAGNI clean extract; no stubs/TODOs; hooks unchanged; systemPatterns updated; import-graph pins match issue #25

## Build checklist

- [x] Step 1–2: import-graph tests (red then green)
- [x] Step 3: `stockroom.home` extract + warehouse re-exports
- [x] Step 4: `torch_source` → `stockroom.home`
- [x] Step 5: full suite + lint/format
- [x] Step 6: systemPatterns heal-import note (hooks unchanged)

## Preflight Amendments

- Strengthened B1 to also pin `python -m stockroom shim --help` (dispatcher path), not only bare `import stockroom.shim`.
