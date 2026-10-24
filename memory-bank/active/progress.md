# Progress

Start the check from the Claude Code and Cursor session-start hooks. Session start returns at once. The launch detaches the way the dashboard does, in a new session that keeps none of the hook's output streams. Cursor's `beforeSubmitPrompt` hook does not launch the check. A test runs the launched entry point against a final record and proves it does not build. A stockroom home with no warehouse still ingests from the schema file, embed and semantic answer, and the launched check records the warehouse as already new and builds nothing.

**Complexity:** Level 2

## 2026-10-24 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Checked milestone 6 after its reflect phase
    - Removed the milestone 6 sub-run files
    - Classified milestone 7, the session-start launch, as Level 2
* Decisions made
    - Level 2. The check pass already exists. This sub-run starts that pass from the two session-start hooks and returns at once. The L4 milestone already fixes the detach, which hooks launch, and the new-install proof, so this sub-run does not reopen architecture
* Insights
    - Shipping this milestone turns the rehearsal and the swap on for every install that updates

## 2026-10-24 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 2 plan for the session-start launch
* Decisions made
    - The hook runs `python -m stockroom.check` on the same interpreter rectify uses. There is no `stockroom check` subcommand
    - The parent spawns a child with the dashboard detach flags and returns. Only the child calls `entry`
    - The new-install proof uses empty transcript roots and `FakeEncoder`
* Insights
    - A bare `&` in the Cursor session-start command can hold the hook open, because that command discards stdout and leaves stderr open

## 2026-10-24 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the milestone 7 session-start launch plan against the check pass, the hook commands, and the test runner
    - Recorded `FAIL (fixable)` in `memory-bank/active/.preflight-status`
* Decisions made
    - The red-test steps that wait on `launch` must set `PYTHONPATH` to the engine `src` directory. `launch` keeps inheriting the environment the hook already sets
    - Unit 4 must also update `docs/user-guide/load/schedule.md` and `docs/user-guide/installed-layout.md`, which still say session start only rectifies the shim and launches the dashboard
* Insights
    - pytest's `pythonpath` does not reach a child process, and `uv run` does not set `PYTHONPATH`. The child's stderr is `DEVNULL`, so the import error shows up only as a non-zero exit

## 2026-10-24 - PLAN - COMPLETE

* Work completed
    - Revised the session-start launch plan for both fixable findings
* Decisions made
    - Tests that wait on `launch` set `PYTHONPATH` to `_SRC` before the call. `launch` passes no `env` and inherits the parent environment
    - Unit 4 now includes `docs/user-guide/load/schedule.md` and the `hooks/` row in `docs/user-guide/installed-layout.md`
    - The DuckDB-import advisory stays out of the plan
* Insights
    - The hook already exports `PYTHONPATH` for the parent. The gap was only the pytest process

## 2026-10-24 - PREFLIGHT - COMPLETE

* Work completed
    - Re-validated the revised milestone 7 session-start launch plan against the check pass, the hook commands, and the test runner
    - Recorded `PASS WITH ADVISORY` in `memory-bank/active/.preflight-status`
* Decisions made
    - The plan is acceptable as written. No test step moved, and no step was struck
    - The stdlib launcher split stays an advisory. `entry` and `run_check` stay unchanged
* Insights
    - `resolve_home()` returns `(Path, str)`. `launch` and `entry` take the path
    - After unit 1, the new-install proof is already green. Unit 3 does not go red

## 2026-10-24 - BUILD - COMPLETE

* Work completed
    - Added `launch` and `main` in front of `entry`
    - Started that module from both session-start hooks, after the dashboard
    - Proved a swapped record does not build, a missing home stays missing, and an empty install records `already-new`
    - Updated the hook descriptions
* Decisions made
    - The no-argument home is `resolve_home()[0]`
    - The DuckDB-import advisory stayed out. `entry` and `run_check` are unchanged
    - The engine suite skipped `tests/test_coverage_collection.py` so the coverage sync would not remove torch
* Insights
    - `stockroom check` was already an unknown command, so that lock test was green before the launch existed
    - The empty-install proof was green on the first run. No production change was required for it

## 2026-10-24 - QA - COMPLETE

* Work completed
    - Reviewed the session-start launch against the milestone 7 plan
    - Wrote `memory-bank/active/.qa-validation-status`
* Decisions made
    - PASS. The implementation is acceptable as-is. Advisories stay advisories
* Insights
    - The hook parent still imports DuckDB before `launch` returns. The plan left that split out
    - Lifecycle's doctrine still calls a repeated session start a no-op. The new section states the rehearsal and the later swap
    - The architecture index and packaging still say every caller goes through the shim. Lifecycle says the check does not
