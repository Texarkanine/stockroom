# Active Context

## Current Task: plugin-root-resolution
**Phase:** PREFLIGHT - COMPLETE (FAIL (fixable)) (rework round 4: paths with a space or `'` in shell text)

## What Was Done
- Rounds 1 to 3 are complete through Reflect. Round 3's plan and its build and QA records are in git at 0e458e9.
- Round 4's plan is in `tasks.md`. It holds:
    - an inventory of every place stockroom writes a path into shell text, with a result for a space and for `'` in each;
    - four units and a verification list.
- Breaking today, and fixed by the plan:
    - the nightly cron and launchd entries (Unit 1);
    - the Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` recipes, plus `localdev.sh`'s Claude hint (Unit 2).
- Also planned:
    - a guard test pinning Cursor's typed Step 2 path with a space and `'`, plus QA follow-up 1, the error-line wording (Unit 3);
    - prose, patterns, the brief and SumMem (Unit 4).
- Probe scripts (scratch, outside the repo), under `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/`:
    - `schedule_fix_probe.py`
    - `make_quoting_probe.sh`
    - `error_line_probe.sh`

## Decisions
- **Operator decisions (2026-10-18):**
    - Fix what is both common and breaking: a space or `'` in a path. `$`, a backtick, `"`, `\` and `%` are out of scope, and are listed instead.
    - Fix every instance, not one.
- Earlier operator decisions stand (round 3's plan at 0e458e9, and the brief).
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run.
- **Plan decisions:**
    - Scheduler: `shlex.quote` on the log path, the `PATH=` value and the whole payload. Plain paths render byte for byte as today.
    - Makefile: double quotes around the `$(CURDIR)` paths.
    - The error-line wording has no test of its own: it is prose, and the existing tests run both branches.

## For the PR #142 text (collected)
- Users whose stockroom home holds a space should re-run `stockroom schedule install`, because Step 8 skips an entry that is already installed.
- The empty `data/stockroom-inline` folder (round 3, preflight advisory 6).

## Next Step
- Preflight runs in a subagent.
