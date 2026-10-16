# Active Context

## Current Task: plugin-root-resolution
**Phase:** PLAN - COMPLETE (rework round 1: PR #142 review fixes)

## What Was Done
- First pass shipped on `claudeboarding` and is PR #142, at 7f3917f: the Step 2 install-layout owner rule, dead-shim replacement in `rectify`, and Step 7 triage. QA PASS, reflected. The reflection is at `memory-bank/active/reflection/reflection-plugin-root-resolution.md`.
- The operator asked for the PR's review feedback to be judged. Six bot inline comments were all valid and reproduced, and all were judged "fix in this PR". The operator said "fix all of those" and invoked `/niko-plan`.
- The rework plan is in `tasks.md`. It has 5 units:
    1. `_alive` counts an uncheckable engine as alive (executable).
    2. The Step 2 default-folder owner rule and a shell-safe printed line (executable).
    3. Step 7: the synced row and uncheckable engines (prose).
    4. `systemPatterns.md` and SumMem (prose).
    5. Verification.

## Decisions
- Operator decisions from 2026-10-16 still stand; they are listed in `tasks.md`.
- **Operator decision (2026-10-16, after the first plan):** "We do not want Cursor users to have to answer extra questions to account for Claude Code situations." Applied in the revised plan:
    - The path decides inside default plugins folders.
    - Elsewhere, `CURSOR_PLUGIN_ROOT` holding this engine gives `cursor`, as in the first pass.
    - Otherwise `OWNER` is empty: Claude Code asks the user, and other harnesses name themselves with no question.
    - Claude Code's substituted plugin root no longer decides the owner, because `--plugin-dir` substitutes a checkout too.
- The cost lands on Claude Code users only: those with `CLAUDE_CONFIG_DIR` or `CLAUDE_CODE_PLUGIN_CACHE_DIR` get one question. A fallback is written in `tasks.md`.
- Accepted Cursor residual: a cache-shaped checkout read through its real path with no `CURSOR_PLUGIN_ROOT` still gets `cursor` from the agent.
- An uncheckable engine dir counts as alive. Only ENOENT, ENOTDIR and ELOOP mean dead, which is the same on Python 3.11 to 3.14.

## Next Step
- Preflight (subagent) on the revised plan, then Build.
