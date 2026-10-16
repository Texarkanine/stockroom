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

## 2026-10-16 - PREFLIGHT (second run) - COMPLETE

* Work completed
    - Checked the revised plan (b44920d) against the codebase. Both findings from the first preflight are resolved.
    - Wrote a prototype of the target Step 2 block, with a helper that reads a named variable. All nine planned cases gave the planned results under dash and bash, including the logical mirror `APP_DIR`.
    - Probed Claude Code 2.1.301 headless with an argument-taking project skill.
    - Result (first line of `.preflight-status`): `FAIL (fixable)`.
* Decisions made
    - TDD encoding passes: Unit 1 puts its tests first, and Units 2 and 3 are prose. No strike or swap was needed.
    - Fixable 1: Claude Code also substitutes `$0`…`$N` (and `$ARGUMENTS`) in skill text when the skill gets arguments, inside code fences too. The probe confirmed it: `/argprobe alpha beta` turned `"$1"` into `"beta"` inside a shell function. A `holds_engine` helper that takes `$1` would break the root guard, and the planned test would not notice. Fix:
        - Correct the evidence.
        - Allow no `$<digit>` in the SKILL.md body. The helper reads a named variable, set in its own statement.
        - Add a "Claude rendering with arguments" test case.
* Insights
    - Advisories:
        - Step 7 should pass `--app-dir "$APP_DIR"`, or the bake is physical and differs from the hook's logical bake.
        - Shell-quote the printed re-set line, because WSL Windows user names can contain spaces.
        - zsh is absent here and in CI, so the zsh case always skips.
        - Checking the path rule before the root rules removes the "Cursor fills the Claude token" misroute.
        - Fence selection breaks if Build adds a fence that shows the re-set prefix.
        - An optional case for a Claude project-skill checkout, which should resolve to `dev`.
    - Radical idea (advisory): ownership follows the baked tree. `shim.rectify` adopts a foreign shim baked inside the same harness plugin install, so this bug's existing victims heal at their next session start.

## 2026-10-16 - PLAN (third revision, operator decisions) - COMPLETE

* Work completed
    - Wrote a failure-mode analysis of entering and leaving dev for the operator. Under the documented flow, the only real stuck path is a dead `dev` shim (deleted checkout), which hooks never touch. The every-prompt Cursor hook adds no new failure class.
    - Rewrote the plan around the operator's decisions. Brief UC3/UC4, constraints and ACs updated.
* Decisions made
    - Operator decisions:
        - Contributors always get `dev`. A real install is a marketplace cache copy (`…/cache/<marketplace>/<plugin>/<version>`).
        - Hooks are unchanged.
        - `rectify` replaces a dead shim of any owner, but never a live foreign one or an unparseable file.
        - No separate dev data.
        - Argument substitution is not a concern.
    - The shim's missing-dir remedy for `dev` mentions starting a session of an installed harness plugin. A new template placeholder; the env-not-ready remedy is unchanged.

## 2026-10-16 - PREFLIGHT (third run) - COMPLETE

* Work completed
    - Checked the third-revision plan (951e756) against the codebase: `sr-initialize` SKILL.md, `stockroom.shim` and its template, the shim, CLI and runtime tests, hygiene and packaging tests, `localdev.sh`, the Makefile, and the docs that state the rectify policy.
    - Wrote the target Step 2 block in scratch and ran all 13 planned cases under dash, bash and busybox sh. Every case gave the planned `OWNER` and `APP_DIR`.
    - Checked the Claude Code plugin-loading docs. `CLAUDE_CODE_PLUGIN_CACHE_DIR` replaces the plugins root, and copies stay at `<root>/cache/<m>/<p>/<v>`. Warehouse history shows Cursor runs `sr-initialize` from `~/.cursor/plugins/cache/…`.
    - Result (first line of `.preflight-status`): `PASS WITH ADVISORY`.
* Decisions made
    - TDD encoding passes. Units 1 and 3 put tests first, Unit 2 is wording guarded by the existing runtime tests, and Units 4 and 5 are prose. No strike or swap was needed.
* Insights
    - Advisories:
        - Plugins synced from claude.ai (`<plugins root>/synced/…`) are real installs, but the layout rule calls them `dev`. This needs an operator call.
        - The Pre-Mortem's "visible failure" claim is wrong, because install dirs contain a Makefile.
        - Settle stop-versus-name-your-harness when `OWNER` is empty.
        - Step 7 should read `~/.local/bin/stockroom`, not `command -v`.
        - Stale "never touches a foreign owner" text in `shim.py` help, the `ShimReport` docstring, the `test_shim.py` docstring, packaging.md line 17 and troubleshooting line 34.
        - The "Red today" labels are inaccurate.
        - Check exactly three levels below `cache`.
    - Radical idea (advisory): a stdlib-only `stockroom shim triage` verb, so Step 7 becomes a tested lookup.
