# Progress

Reassess how each harness exposes its plugin root (`CLAUDE_PLUGIN_ROOT`, `CURSOR_PLUGIN_ROOT`) to hooks, skill content and agent-run shell commands. Then fix `sr-initialize` context detection and engine-dir resolution, audit both hook files, correct docs that state the wrong model, and pin the detection contract with tests.

**Complexity:** Level 2

## 2026-10-16 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Read the bug report at `.scratch/stockroom-bug-claude-plugin-root-unset.md`, plus the `sr-initialize` skill, both hook files and the related tests.
    - Confirmed in the Claude Code docs, and reproduced on 2.1.301, that `CLAUDE_PLUGIN_ROOT` is absent from the Bash tool environment.
* Decisions made
    - Level 2: a bug fix across the skill, tests, docs and possibly hooks, with no architectural change.
* Insights
    - The Claude hook is likely correct: hook commands get both inline substitution and the exported variable. The skill is the broken surface.
    - Cursor documents `${CURSOR_PLUGIN_ROOT}` expansion only for MCP config. Hook and skill behavior there is undocumented.

## 2026-10-16 - PLAN - COMPLETE

* Work completed
    - Probed Claude Code 2.1.301 headless with a throwaway plugin and a project skill. In plugin skills, only the exact tokens `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}` are substituted; in project skills, only `${CLAUDE_SKILL_DIR}`.
    - Gathered Cursor evidence: staff endorse `${CURSOR_PLUGIN_ROOT}` in hooks; the variable is undocumented for agent shells and skill text.
    - Checked real install dirs: both harness caches contain `.git` and `Makefile`.
    - Audited both hook files (`claude plugin validate .` passes) and the docs.
    - Wrote the L2 plan to `tasks.md`: a 5-rule Step 2 resolution, a guarded Step 7 install, two doc fixes, and a new `test_initialize_context.py` that runs the Step 2 block under modeled harness rendering.
* Decisions made
    - Take `APP_DIR` from this skill's sibling directory, never from a plugin-root variable. Plugin-root signals pick only `OWNER`.
    - Owner order: no engine → none; `${CURSOR_PLUGIN_ROOT}` → cursor; `${CLAUDE_PLUGIN_ROOT}` (substituted) → claude; `*/.cursor/plugins/*` or `*/.claude/plugins/*` path → that harness; otherwise dev.
    - Hooks unchanged: they already receive the root by the documented mechanism.
    - `claude --plugin-dir <checkout>` resolves to `claude`, matching that session's own SessionStart hook.
* Insights
    - "Makefile plus .git means dev", the bug report's option 3, would misfire: marketplace installs are git clones that include the Makefile.
    - The bug has existed since plugin 0.1.1. Agents improvised silently, which is why nobody noticed.

## 2026-10-16 - PREFLIGHT - COMPLETE

* Work completed
    - Checked the L2 plan against the codebase: `skills/sr-initialize/SKILL.md`, `stockroom.shim`, `scripts/localdev.sh`, the Makefile, both hook files, the test conventions, and the contributor and troubleshooting docs.
    - Result (first line of `.preflight-status`): `FAIL (fixable)`.
* Decisions made
    - TDD encoding passes: Unit 1 puts its tests first, and Units 2 and 3 are prose. No strike or swap was needed.
    - Fixable 1: the localdev-mirror test expects `APP_DIR=<repo>/skills/sr-search`, but logical `cd && pwd` gives the symlinked mirror path `<repo>/.cursor/skills/stockroom-local/sr-search`. Checked under dash.
    - Fixable 2: Step 7's "always install, then offer takeover" would push takeover prompts onto healthy shims: a live shim owned by the other harness, and a contributor's deliberate `dev` claim. Step 7 needs to sort shims by the header's owner and `STOCKROOM_APP_DIR`. Offer a takeover only for a `dev` shim baked inside a harness plugins tree, or a dead foreign shim.
* Insights
    - Advisories: check that each plugin-root variable contains `APP_DIR`; the `--plugin-dir` owner differs from brief UC3; shell variables do not carry between Claude Code Bash calls; parametrize test shells; `CDPATH=''`; troubleshooting says a live foreign shim needs only `--takeover`, but it needs `--takeover --force`.
    - Radical idea (advisory): a stdlib-only engine resolver (`shim context`), with `doctor probe` reporting owner and mis-owned facts.

## 2026-10-16 - PLAN (revision after preflight) - COMPLETE

* Work completed
    - Fixed preflight finding 1: the localdev-mirror case now expects the logical mirror `APP_DIR` and checks its resolved target separately.
    - Fixed preflight finding 2: Step 7 now sorts an existing shim by its header owner and baked dir. It offers a consented takeover only for a dead foreign shim, or for a `dev` shim baked inside a harness plugins tree. Every maintained shim is left alone.
    - Folded in the advisories:
        - A1: a plugin root counts only when it physically holds this engine; there is a leaked-root test case.
        - A3: re-set the printed values in every later command, and stop when `OWNER` is empty.
        - A4: tests run under sh, bash and zsh, skipping absent shells.
        - A5: `CDPATH=''`, a POSIX placeholder, and `printf`.
        - A6: the troubleshooting line about takeover flags, and `--plugin-dir` in the preparation wording.
        - A7: check whether the live shim is baked to this worktree before restoring torch.
* Decisions made
    - A2: `claude --plugin-dir <checkout>` resolves to `claude`, the same owner as that session's own SessionStart hook. Brief UC3 and AC3 updated; flagged for the operator.
    - Declined the radical engine `shim context` resolver: a block-execution test is still the only guard on the skill's substitution contract. `doctor probe` mis-owned detection is logged as a follow-up.
