# Task: parallel-pytest-xdist

* Task ID: parallel-pytest-xdist
* Complexity: Level 2
* Type: simple enhancement

Enable safe process-level parallel pytest for the engine suite: lock `pytest-xdist`, default workers via pytest `addopts`, keep isolation contracts green under multi-worker runs.

## Test Plan (TDD)

### Behaviors to Verify

- Declared dep: engine `pyproject.toml` `dependency-groups.dev` includes `pytest-xdist` with a compatible pin (`~=3.0`) → parseable and present
- Locked: committed `uv.lock` contains a `pytest-xdist` package entry (and thus its `execnet` transitive) → hermetic install possible
- Default workers: `[tool.pytest.ini_options].addopts` is a list including `"-n"` and `"auto"` → bare `pytest` / Make / CI inherit parallelism without duplicated flags
- Override still possible: documenting that `-n0` (or explicit `-n N`) overrides `addopts` for serial debugging → contributor docs state this
- Regression: full engine pytest suite under `-n auto` (via `make test` / CI-equivalent) stays green, including warehouse concurrency and dashboard server tests that spawn subprocesses / bind ports

### Edge Cases

- Ad-hoc single-file runs still work with workers (xdist distributes one or few tests across workers without error)
- `test-dashboard-py` slice inherits the same `addopts` (no separate serial-only path unless a failure forces one)
- WSL / low-core machines: `-n auto` is acceptable default; no hard-coded huge worker count
- Golden rewrite env vars (`STOCKROOM_UPDATE_*`) remain opt-in and must not race-write when unset (existing behavior)

### Test Infrastructure

- Framework: pytest (engine `skills/sr-search/`)
- Test location: extend `skills/sr-search/tests/test_lock_hermetic.py` for dep/lock/addopts contracts (same file already parses `pyproject.toml` / `uv.lock`)
- Conventions: module-scoped `pyproject` / `lock` fixtures; assertion-style contract tests; no new runner
- New test files: none

## Implementation Plan

1. **Failing contract tests for xdist + default workers** ✅
   - Files: `skills/sr-search/tests/test_lock_hermetic.py`
   - Changes: add tests that (a) `pytest-xdist` appears in `dependency-groups.dev`, (b) lock packages include `pytest-xdist`, (c) `tool.pytest.ini_options.addopts` is a list containing `"-n"` and `"auto"`. Run → expect fail before dep/config land.

2. **Add locked `pytest-xdist` and pytest `addopts`** ✅
   - Files: `skills/sr-search/pyproject.toml`, `skills/sr-search/uv.lock`
   - Changes: add `pytest-xdist~=3.0` to `[dependency-groups] dev`; set `addopts = ["-n", "auto"]` under `[tool.pytest.ini_options]` (preserve existing `testpaths` / `pythonpath`); regenerate lock hermetically (`uv lock --no-config` / `make lock`). Re-run contract tests → green.

3. **Verify Make / CI inherit workers (no flag duplication)** ✅
   - Files: `Makefile`, `.github/workflows/ci.yml` (read-only unless a comment is useful)
   - Changes: keep invocations as plain `pytest` so `addopts` is the single source of truth; only edit if a target bypasses project config. Smoke: `uv run --no-sync --no-config pytest -q` reports “bringing up nodes”.

4. **Full parallel suite + isolation fixes if needed** ✅
   - Files: whatever tests fail under `-n auto` (likely none; candidates: `test_warehouse_concurrency.py`, `test_dashboard_server.py`)
   - Changes: TDD-fix any shared-state bleed (always via `warehouse_home` / `tmp_path`, never threaded parallel). Gate: full `make test` green.
   - Result: no isolation fixes needed — `make test` → 586 passed, 4 skipped, 86 JS in ~19s pytest wall with 16 workers.

5. **Contributor docs** ✅
   - Files: `docs/contributing/iteration.md`; `memory-bank/techContext.md` (Testing Process pointer)
   - Changes: note that engine pytest defaults to process workers via `pytest-xdist` (`-n auto`); serial override with `pytest -n0 …` for debugging.

## Technology Validation

**New dependency:** `pytest-xdist~=3.0` (pulls `execnet`).

**PoC (2026-07-17, reverted after validation so build can TDD cleanly):**
- `uv add --dev 'pytest-xdist~=3.0' --no-config` in `skills/sr-search` resolved/installed `pytest-xdist==3.8.0` + `execnet==2.1.2`
- `uv run --no-sync --no-config pytest -n 2 tests/test_smoke.py tests/test_warehouse_lock.py -q` → 6 passed (“bringing up nodes…”)
- Tree restored to pre-PoC `pyproject.toml` / `uv.lock` afterward

## Dependencies

- Existing pytest harness + `test_lock_hermetic.py` contract style
- Root `Makefile` `test` / `test-dashboard-py` and CI engine job already invoke project-local pytest
- Per-test `warehouse_home` / `tmp_path` isolation in `tests/conftest.py`

## Challenges & Mitigations

- **Warehouse concurrency tests spawn subprocesses under xdist workers → CPU thrash / flake:** Mitigation — keep `-n auto` (not a huge fixed N); if flake appears, serialize that module with `pytest.mark.xdist_group` / file-level load strategy rather than abandoning parallelism
- **Duplicate `-n` flags in Make and CI drift from pyproject:** Mitigation — Step 3 keeps Make/CI as bare `pytest`; `addopts` is SSOT
- **Dependabot / lock churn for execnet:** Mitigation — pin `~=3.0`; existing engine UV Dependabot group already covers `dev` deps

## Pre-Mortem

- **Wrong premise: put `-n auto` only in Makefile/CI and forget ad-hoc `uv run pytest`:** Plan response — Step 2 uses pytest `addopts` so every project-config invocation is parallel
- **Assume suite is isolation-perfect and skip a real multi-worker full run:** already covered by Step 4 gate
- **Treat docs as optional and leave contributors unaware of `-n0`:** already covered by Step 5

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight — PASS (addopts contracted as TOML list `["-n", "auto"]` for unambiguous assertions)
- [x] Build
- [x] QA — PASS (trivial KISS: drop redundant startswith / separate auto asserts in lock hermetic tests)
