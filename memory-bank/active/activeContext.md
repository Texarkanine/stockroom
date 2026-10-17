# Active Context

## Current Task: plugin-root-resolution
**Phase:** PLAN - COMPLETE (rework round 3: Claude Code's plugin data folder)

## What Was Done
- Rounds 1 and 2 are complete through Reflect, and their reflections are in `memory-bank/active/reflection/reflection-plugin-root-resolution.md`. Round 2's plan is in git at fc3db1b.
- After Reflect, the operator asked for `${CLAUDE_PLUGIN_DATA}` to be explored and the older quoting problem explained. Two live probes and a shell demo followed; results are in `progress.md` (2026-10-17, POST-REFLECT probes) and commit fc3db1b.
- Round 3 plan written to `tasks.md`:
    - Unit 1: Step 2 reads Claude Code's pasted paths from a quoted heredoc (executable).
    - Unit 2: Step 2 settles the owner from the substituted data folder (executable).
    - Unit 3: Step 2 prose in `SKILL.md`.
    - Unit 4: `systemPatterns.md`, brief AC7 and a new AC10, and a SumMem note.
    - Unit 5: verification, including a live end-to-end check of the real `SKILL.md`.

## Decisions
- **Operator decisions (2026-10-17):**
    - Use `${CLAUDE_PLUGIN_DATA}`, because the docs make it a contract. The docs cover the plugin-id origins (`@inline` is `--plugin-dir`), the reserved names, and `data/<plugin-id>` beside `cache/` in one plugins root.
    - Any failure of the new signal must show up during `sr-initialize`, where the agent can work around it. It must never reach the processes that run without an agent (hooks, `shim rectify`, the nightly job).
    - Quoting: folders built by an attacker are out of scope, and `'` is the only likely special character (it already works). The fix goes in only because it is cheap. It is also what keeps `PLUGIN_DATA` from being read out of the environment.
- Earlier operator decisions stand. They are listed in `tasks.md`, and in full in round 2's plan.
- **Owner rule, `*)` arm:** a data folder in the copy's plugins root or a record listing → `claude`; `stockroom-inline` → `dev`; `CURSOR_PLUGIN_ROOT` → `cursor`; otherwise empty, plus a stderr line that shows the data folder it was given.
- **Hooks unchanged.** The probe showed that shell-form hooks expand `"${CLAUDE_PLUGIN_ROOT}"` from the environment, so they have no quoting problem.
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run.

## Next Step
- Preflight runs in a subagent.
