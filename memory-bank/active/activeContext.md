# Active Context

## Current Task: plugin-root-resolution
**Phase:** REFLECT - COMPLETE (rework round 1: PR #142 review fixes)

## What Was Done
- First pass shipped on `claudeboarding` and is PR #142, at 7f3917f: the Step 2 install-layout owner rule, dead-shim replacement in `rectify`, and Step 7 triage. QA PASS, reflected. The reflection is at `memory-bank/active/reflection/reflection-plugin-root-resolution.md`.
- The six bot inline comments on PR #142 were all judged valid and "fix in this PR". The operator said "fix all of those". Preflight on the revised plan: PASS WITH ADVISORY.
- Build fixed all six. `make ci` is green: pytest 944 passed and 23 skipped, JS 134/134, REUSE compliant.
- Files modified, all under `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-claudeboarding/`:
    - `skills/sr-search/src/stockroom/shim.py`: `_GONE_ERRNOS`; `_alive` stats directly and counts an uncheckable engine as alive; `rectify` docstring.
    - `skills/sr-search/tests/test_shim.py`: the `needs_non_root` marker, the `uncheckable_dir` fixture, `_lock`, and 2 new tests.
    - `skills/sr-search/tests/test_initialize_context.py`: module docstring; `_run_block` reads back through the printed line; 4 new tests; 2 changed expectations (Claude custom root, leaked Cursor root → empty `OWNER`).
    - `skills/sr-initialize/SKILL.md`: the Step 2 block and its prose; the Step 7 liveness check, a "cannot be checked" row, and the mislabel row.
    - `memory-bank/systemPatterns.md`: the owner rule and the liveness wording.
    - `memory-bank/active/projectbrief.md`: AC1 and AC8 narrowed; AC7 to AC9 added.
    - Two new `.summem/notes/*`, plus one SumMem nap.

## Decisions
- Operator decisions from 2026-10-16 still stand; they are listed in `tasks.md`.
- **Operator decision (2026-10-16, after the first plan):** "We do not want Cursor users to have to answer extra questions to account for Claude Code situations." Applied:
    - The path decides inside default plugins folders.
    - Elsewhere, `CURSOR_PLUGIN_ROOT` holding this engine gives `cursor`, as in the first pass.
    - Otherwise `OWNER` is empty: Claude Code asks the user, and other harnesses name themselves with no question.
    - Claude Code's substituted plugin root no longer decides the owner.
- The cost lands on Claude Code users only: those with `CLAUDE_CONFIG_DIR` or `CLAUDE_CODE_PLUGIN_CACHE_DIR` get one question. A fallback is written in `tasks.md`.
- Accepted Cursor residual: a cache-shaped checkout read through its real path with no `CURSOR_PLUGIN_ROOT` still gets `cursor` from the agent.
- An uncheckable engine dir counts as alive. Only ENOENT, ENOTDIR and ELOOP mean dead, which is the same on Python 3.11 to 3.14.

## Deviations from the plan (Build)
- Preflight advisories 1 and 3 to 7 were folded in. The dispositions are in `tasks.md`.
- One added test the plan did not list (advisory 5): a synced copy with the placeholder filled gives `claude`. Cursor agents read skills from Claude Code's plugin folders, so this Cursor outcome changes from `dev` to `claude`, with no question added.
- Step 7's mislabel row now asks first when the path is outside the default plugins folders (advisory 4). That question merges into the consent question the row already asked, so it adds no new prompt.
- Advisory 2 (three other liveness checks) was accepted as gaps, not changed.

## Reflection (rework round 1)
- QA PASS. Five minor QA findings were fixed after QA; finding 1 (a NUL byte made `_alive` raise `ValueError`) was fixed test-first. `make ci` green: pytest 946 passed, 23 skipped.
- The reflection is appended to `memory-bank/active/reflection/reflection-plugin-root-resolution.md`.
- Persistent files: `productContext` and `techContext` skipped; `systemPatterns` was already updated in Build.
- Left for the operator: the version-folder proof idea, which would replace the Claude Code question.

## Next Step
- Operator runs `/niko-archive`. Then push `claudeboarding`, so PR #142 picks up the rework.
