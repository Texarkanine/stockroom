# Active Context

## Current Task: plugin-root-resolution
**Phase:** REFLECT - COMPLETE (rework round 2: Claude Code's install record)

## What Was Done
- Round 1 (PR #142 review fixes) is complete through Reflect. Its plan is in git at 50835fd, and its reflection is in `memory-bank/active/reflection/reflection-plugin-root-resolution.md`.
- Round 2's plan is in `tasks.md`. Preflight result: PASS WITH ADVISORY. Advisory dispositions are listed in `tasks.md`.
- Build completed all 4 units:
    - Unit 1: 8 red (4 tests × sh/bash), then green.
    - Mutation check: an unquoted pattern turns only the orphan case red; removing the record branch turns exactly the 3 recorded tests red.
    - BusyBox check: PASS.
- `make ci` is green: pytest 956 passed and 28 skipped, JS 134/134, REUSE compliant. `claude plugin validate .` passes, with only the existing CLAUDE.md warning.
- Files modified, all under `/home/mobaxterm/worktrees/Texarkanine/stockroom/stockroom-claudeboarding/`:
    - `skills/sr-initialize/SKILL.md`:
        - The Step 2 `*)` arm checks `installed_plugins.json` first, then `CURSOR_PLUGIN_ROOT`, and its stderr text changed.
        - The `claude`/`cursor` owner bullet and the empty-`OWNER` bullet.
        - One sentence in the Step 7 mislabel row.
    - `skills/sr-search/tests/test_initialize_context.py`: `import json`, the `_record_install` helper, 4 new tests (one parametrized over 2 layouts), the module docstring, and one changed test docstring.
    - `memory-bank/systemPatterns.md`: the Dual-manifest owner-rule sentence.
    - `memory-bank/active/projectbrief.md`: AC7.
    - One new `.summem/notes/*` file, plus one SumMem nap.
- Scratch scripts, kept outside the repo, under `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/`: `busybox-step2-check.sh`, `render_step2.py` and `mutation_check.py`.

## Decisions
- Operator decisions from 2026-10-16 still stand; they are listed in `tasks.md`.
- **Operator decision (2026-10-16):** the plan review recommended the install-record check as a follow-up. The operator asked "Why not as part of this PR?", asked for the false-positive risk to be checked, then invoked `/niko-plan then!`. So the check goes into PR #142 as rework round 2. The version-folder proof stays rejected.
- **Operator working rules (2026-10-16):**
    - Agent commits use `--no-gpg-sign`.
    - Probes and checks are written as commented script files in a scratch scripts folder and then run. No big inline shell one-liners.
- The record check comes before the `CURSOR_PLUGIN_ROOT` check. The record is documented; the variable in agent shells is not, and can leak. No test pins the order, because no real copy is both.
- Fails closed: any mismatch leaves `OWNER` empty, which is round 1's behavior.

## Deviations from the plan (Build)
- Unit 2's sentence follows preflight advisory 1. Only an owner the block printed, or the user's own answer, lets the agent skip the checkout question; an owner the agent filled in does not.
- Preflight advisories 2 to 4 were written into `tasks.md` (Challenges, "How it fails", "Who it helps"). They needed no code change.
- Advisory 5 (special characters in the skill folder's path) is a follow-up for Reflect. The `${CLAUDE_PLUGIN_DATA}` radical idea is left for the operator.

## Reflection (rework round 2)
- QA PASS. Its one docstring note was fixed after QA, and the test re-ran green.
- The reflection is appended to `memory-bank/active/reflection/reflection-plugin-root-resolution.md`.
- Persistent files: `productContext` and `techContext` were skipped, because neither states the owner rule or any plugin-install contract. `systemPatterns` was already updated in Build.
- SumMem: a correction note says relative-path local-marketplace plugins load in place (`readFromFolder`), even though they get a cache entry and a record.
- Left for the operator:
    - The `${CLAUDE_PLUGIN_DATA}` idea, which needs a live probe first.
    - The existing `SKILL_DIR="…"` problem with special characters in paths, as a follow-up.

## Next Step
- Operator runs `/niko-archive`. Then push `claudeboarding`, so PR #142 picks up rounds 1 and 2.
