# Active Context

## Current Task: plugin-root-resolution
**Phase:** BUILD - COMPLETE (rework round 3: Claude Code's plugin data folder)

## What Was Done
- Rounds 1 and 2 are complete through Reflect. Round 2's plan is in git at fc3db1b. Round 3's plan is in `tasks.md`, with preflight PASS WITH ADVISORY; the dispositions are in `tasks.md`.
- Build completed all 5 units:
    - Unit 1: 6 red, then green.
    - Unit 2: 6 red, then green.
    - Mutation check M1 to M5: ALL OK.
    - BusyBox check: all 5 cases PASS.
    - `make ci` green: pytest 974 passed and 37 skipped, JS 134/134, REUSE compliant.
    - `claude plugin validate .` passes.
    - Live end-to-end check on Claude Code 2.1.302: PASS.
- Files modified, all under `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-claudeboarding/`:
    - `skills/sr-initialize/SKILL.md`:
        - The Step 2 head is a quoted heredoc reading `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_DATA}`, plus two `case` lines.
        - The `*)` arm adds rule 1 (data folder in the copy's plugins root → `claude`) and rule 3 (`stockroom-inline` → `dev`). Its stderr line names the data folder.
        - Prose: the run paragraph, the custom-folder owner sentence, and the empty-`OWNER` bullets.
    - `skills/sr-search/tests/test_initialize_context.py`:
        - Helpers: `_step2_block` selects the fence by its token; `_render_claude` takes `plugin_data`; `_run_block`'s readback runs with `cwd=home`.
        - 5 new test functions: `test_skill_path_is_read_as_data`, `test_claude_custom_root_install_by_data_folder`, `test_claude_plugin_dir_checkout_in_a_cache_shaped_path_is_dev`, `test_data_folder_in_another_plugins_root_proves_nothing`, `test_leaked_plugin_data_variable_is_ignored`.
        - The module docstring and 3 existing test docstrings.
    - `memory-bank/systemPatterns.md`: the plugin-root paragraph (tokens, heredoc, owner rule).
    - `memory-bank/active/projectbrief.md`: UC3, AC3 and AC7, plus a new AC10.
    - Two new `.summem/notes/*` (the round 3 owner rule; the heredoc read), plus the naps the tool asked for.
- Scratch scripts, outside the repo, under `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/`:
    - `mutation_check_r3.py`
    - `live_step2_check.sh` and `extract_rendered_step2.py`
    - Preflight's `busybox_target_check.sh` and `render_both.py`, which are in `scratchpad/preflight-r3/scripts/`.

## Decisions
- **Operator decisions (2026-10-17):**
    - Use `${CLAUDE_PLUGIN_DATA}`, because the docs make it a contract.
    - Any failure must show up during `sr-initialize` and never reach hooks, `shim rectify` or the nightly job.
    - The quoting fix goes in only because it is cheap.
- Earlier operator decisions stand (`tasks.md`; in full in round 2's plan).
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run.
- The rules in the `*)` arm run in this order: data folder or record → `claude`; `stockroom-inline` → `dev`; Cursor root → `cursor`; otherwise empty. The order of the record check and the inline check is not pinned (accepted).

## Deviations from the plan (Build)
- Preflight advisories 1 to 5, 7 and 8 were applied as listed in `tasks.md`, under "Preflight advisories: dispositions". Advisory 6 (the empty `data/stockroom-inline` folder) is for the PR text. The `PROOF`-field idea is left for the operator.
- The BusyBox check used preflight's `busybox_target_check.sh`, which covers rules 1 and 3, instead of an updated round 2 script.
- One Unit 3 test run was piped through `tail`, against the test rules. It was re-run unfiltered at once (66 passed), and the full suite ran in `make ci`.

## Next Step
- QA runs in a subagent.
