# Active Context

## Current Task: plugin-root-resolution
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Rounds 1 to 3 are complete through Reflect. Round 3's plan and its build and QA records are in git at 0e458e9.
- Round 4's plan failed its first preflight, fixable (c0fc32f), and passed the second with advisory (db85232). The dispositions are in `tasks.md`.
- Build completed all 6 units. The results are in `tasks.md` under "Build progress".
    - Unit 1: 6 red, then green.
    - Unit 2: 6 red, then green.
    - Unit 3: 10 red, then green.
    - Unit 4: the guard test was green by design.
    - Mutation check M1 to M8: ALL OK.
    - BusyBox: 5/5.
    - `make ci`: green.
    - `claude plugin validate .`: passes.
- QA run 1 failed, fixable: `stockroom doctor smoke` prints its torch command with the engine path unquoted. The Build rerun (`tasks.md`, "Build rerun") fixed it:
    - Red: 2. Green: the doctor tests pass. M9 and M10 were added, and the mutation check M1 to M10 is ALL OK.
    - It took QA advisories 1 (Step 8 says what `entry home: unreadable` means) and 2 (the fresh cron status test runs over odd homes).
    - `make ci` is green (pytest 1008 passed, 38 skipped), and `claude plugin validate .` passes.
- QA run 2 failed, fixable: the older doctor test still asserted the unquoted `--directory <path>`, so it failed from a checkout under `Jane Doe` or `O'Brien`. Build rerun 2 made it compare against the quoted form. From odd-folder copies of the whole suite, no failure is left that only an odd folder causes.
- Files modified, all under `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-claudeboarding/`:
    - `skills/sr-search/src/stockroom/schedule.py`:
        - `shlex.quote` on the log path, the `PATH=` value, `STOCKROOM_HOME=` and the payload.
        - `_cron_entry` and `_launchd_job` now render both entries.
        - Both entries carry `STOCKROOM_HOME`.
        - `cron_status` and `launchd_status` take `which` and report `up-to-date:` and `entry home:`, through the new `_cron_up_to_date` and `_cron_entry_home`.
        - Docstrings and parser help updated.
    - `skills/sr-search/tests/test_schedule.py`: 2 run-the-entry tests (× 3 folders) and 6 status tests, plus the 2.1.1-rendering helpers. The existing status tests pass `fake_which`.
    - `skills/sr-search/tests/test_contributor_paths.py` (new): Make targets (4 × 3 folders) and the localdev hint (× 3).
    - `Makefile`: the `torch`, `shim`, `local-engine` and `local-dashboard` recipes double-quote `$(CURDIR)` paths, and the comment above `shim` explains why.
    - `scripts/localdev.sh`: the Claude hint double-quotes the checkout path.
    - `skills/sr-search/tests/test_initialize_context.py`: `test_cursor_placeholder_path_survives_a_quote_and_a_space`.
    - `skills/sr-initialize/SKILL.md`: the Step 2 error line and its sub-bullet, the opening idempotency paragraph, and Step 8's `status` facts and actions.
    - `docs/user-guide/load/schedule.md` and `docs/user-guide/troubleshooting/index.md`.
    - `memory-bank/systemPatterns.md`: the scheduler sentence, and the new section "Paths in shell text are quoted".
    - `memory-bank/active/projectbrief.md`: AC10 wording, plus new AC11 and AC12.
    - Build rerun: `skills/sr-search/src/stockroom/doctor.py` (`shlex.quote` on the engine path in the torch command), `skills/sr-search/tests/test_doctor.py` (a new test over 3 folders), `test_schedule.py` (the fresh cron status test runs over `_FOLDERS`), `SKILL.md` Step 8 (`unreadable`), `systemPatterns.md` (printed commands), and brief AC11.
    - `.summem/notes/*` and `.summem/naps/*`: 3 notes and 3 naps, all through the tool.
- Scratch scripts are outside the repo, under `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/`:
    - `mutation_check_r4.py`
    - the plan's probes
    - preflight's `error_line_render.sh` (in `preflight-r4b/scripts/`)
    - round 3's `busybox_target_check.sh` (in `preflight-r3/scripts/`)

## Decisions
- **Operator decisions (2026-10-18):**
    - Fix what is both common and breaking: a space or `'` in a path. `$`, a backtick, `"`, `\` and `%` are out of scope; they are listed instead.
    - Fix every instance, not one.
- Earlier operator decisions stand (round 3's plan at 0e458e9, and the brief).
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run.
- **Plan decisions:**
    - Carry the resolved home in both entries, always.
    - Report stale entries through `status`. A re-install needs the user's consent.
    - `XDG_CONFIG_HOME` and the source overrides are not carried (Inventory 2).
    - The `stockroom schedule run` idea and a hook-driven re-render were not applied.

## Deviations from the plan (Build)
- M5 and M6 turn 5 tests red, not the 4 in the plan table. The fresh status tests also assert `entry home:`, which preflight 2's advisory 2 added after that count was made. Predicted in the script before the run.
- The mutation check is a new script, `mutation_check_r4.py`, which mutates the built HEAD. Preflight's runner rebuilt the target from its own edits, so it could not test the code Build wrote. It follows that runner's design: `git archive` copies, exact single-match edits, and poison stand-ins.
- `systemPatterns.md` leaves out the `status` fact names, which are detail for one subsystem (that file's own rule). It states the cross-cutting part: the nightly job sees only what its entry carries.
- Build rerun: M3 and M4 were first predicted at 2 red, and turned 4. The fresh status test, now run over odd homes, also catches them, and both mutants really break the entry. The predictions were corrected and the check repeated.
- One editing slip in Unit 4: adding the guard stub removed the next test's `def` line. It was restored before any run or commit.

## For the PR #142 text (collected)
- Custom-home users' nightly jobs have used the default warehouse. They should re-run `sr-initialize`, or `stockroom schedule install --time HH:MM` with their own time (without `--time` it resets to 03:30).
- The empty `data/stockroom-inline` folder (round 3, preflight advisory 6).

## Next Step
- QA runs again (run 3), in a subagent.
