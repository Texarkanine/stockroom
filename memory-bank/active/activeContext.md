# Active Context

## Current Task: plugin-root-resolution
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY) (rework round 4, revised plan)

## What Was Done
- Rounds 1 to 3 are complete through Reflect. Round 3's plan and its build and QA records are in git at 0e458e9.
- The first round 4 plan (c0fc32f) failed preflight, fixable. The nightly entries carry only `PATH`, so the job always uses the default warehouse, and a custom-home user's job would fill a second one.
- The revised plan is in `tasks.md`. It holds two inventories, five units and a verification list.
    - The two inventories:
        - every place stockroom writes a path into shell text;
        - every variable the nightly job needs from the user's environment.
    - Unit 1: the nightly entries quote every path and carry the resolved `STOCKROOM_HOME`.
    - Unit 2: `schedule status` reports `up-to-date: yes|no|unknown`, and Step 8 offers to re-install an out-of-date entry.
    - Unit 3: the Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` recipes, plus `localdev.sh`'s Claude hint.
    - Unit 4: a guard test for Cursor's typed Step 2 path, and the clearer error line (QA follow-up 1 and preflight advisory 2).
    - Unit 5: prose. Step 2 and Step 8, the scheduling doc, `systemPatterns.md`, the brief (AC11, AC12) and SumMem.
    - Verification: 8 mutants, BusyBox, `make ci`, and `claude plugin validate`.
- Probe scripts are scratch files outside the repo, under `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/`:
    - `schedule_fix_probe.py`
    - `schedule_home_probe.py`
    - `make_quoting_probe.sh`
    - `error_line_probe.sh`
    - Preflight's scripts are in `scratchpad/preflight-r4/scripts/`.

## Decisions
- **Operator decisions (2026-10-18):**
    - Fix what is both common and breaking: a space or `'` in a path. `$`, a backtick, `"`, `\` and `%` are out of scope; they are listed instead.
    - Fix every instance, not one.
- Earlier operator decisions stand (round 3's plan at 0e458e9, and the brief).
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run.
- **Plan decisions (revised):**
    - Preflight finding 1, option (a): carry the resolved home in both entries, always. `XDG_CONFIG_HOME` and the source overrides are not carried; Inventory 2 gives the reasons.
    - Preflight advisory 1: existing entries are reported as out of date, and are re-installed only with the user's consent. Every entry installed before this change shows as out of date once.
    - The `stockroom schedule run` idea is not applied.

## For the PR #142 text (collected)
- Custom-home users' nightly jobs have used the default warehouse. They should re-run `sr-initialize`, or `stockroom schedule install --time HH:MM` with their own time (without `--time` it resets to 03:30).
- The empty `data/stockroom-inline` folder (round 3, preflight advisory 6).

## Next Step
- Preflight runs again, in a subagent.
