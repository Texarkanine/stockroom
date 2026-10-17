# Active Context

## Current Task: plugin-root-resolution
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY) (rework round 2: Claude Code's install record)

## What Was Done
- Round 1 (PR #142 review fixes) is complete through Reflect. QA PASS; `make ci` green with pytest 946 passed and 23 skipped. Its plan is in git at 50835fd, and its reflection is in `memory-bank/active/reflection/reflection-plugin-root-resolution.md`.
- A plan review of preflight's version-folder idea gave the verdict "revise". It recommended Claude Code's install record (`installed_plugins.json`) instead.
- Probes on Claude Code 2.1.302 confirmed the record lists only copied installs, never a checkout. Relative-path local-marketplace plugins load in place (`readFromFolder`). A live session substitutes exactly the recorded `installPath`. Details are under Evidence in `tasks.md`.
- Planned round 2 in `tasks.md`. It has 4 units:
    1. The Step 2 record check (executable).
    2. A Step 7 sentence (prose).
    3. `systemPatterns`, brief AC7 and SumMem (prose).
    4. Verification.
- The target block was prototyped in a scratch copy of the repo. It passes all existing cases plus the draft cases. The red set against today's block matches the plan. A mutant without the pattern's quotes is caught. BusyBox passes.

## Decisions
- Operator decisions from 2026-10-16 still stand; they are listed in `tasks.md`.
- **Operator decision (2026-10-16):** the plan review recommended the install-record check as a follow-up. The operator asked "Why not as part of this PR?", asked for the false-positive risk to be checked, then invoked `/niko-plan then!`. So the check goes into PR #142 as rework round 2. The version-folder proof stays rejected.
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run. No big inline shell one-liners.
- The record check comes before the `CURSOR_PLUGIN_ROOT` check. The record is documented; the variable in agent shells is not, and can leak. The order is not pinned by a test, because no real copy is both.
- Fails closed: any mismatch leaves `OWNER` empty, which is round 1's behavior.

## Next Step
- Preflight (subagent) on the round 2 plan.
