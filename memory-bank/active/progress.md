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

## 2026-10-16 - BUILD - COMPLETE

* Work completed
    - `shim rectify` replaces a dead shim of any owner. Live foreign shims and unidentified files stay a noop. TDD: 2 red, then green.
    - New dead-checkout remedy for `dev` shims (`{{GONE_REMEDY}}`).
    - `sr-initialize` Step 2 rewritten. Install layout decides real versus `dev`, and Claude Code's substitution or Cursor's env attributes custom roots. `test_initialize_context.py` covers 14 cases under each installed shell. It went red first, because there was no `SKILL_DIR=` fence, then green.
    - Step 7 triage table, docs, `systemPatterns.md`, and the `localdev.sh` comment.
    - Gates:
        - lint, format, schema docs, JS tests and REUSE pass.
        - pytest: 931 passed, 18 skipped. The only failure is the docs-lock test under local uv 0.8.22; it passes under uv 0.12.22.
        - An e2e run on real Claude Code 2.1.301 confirms the shipped Step 2 resolves `claude` through substitution.
* Decisions made
    - A non-stockroom file at the shim path is replaced only with consent.
    - A dead foreign shim is replaced without asking.
* Insights
    - The `-c` script approach lets the shipped skill fence run as a real program under each shell, so a regression to an unbraced token fails CI (mutation-checked).

## 2026-10-16 - QA - COMPLETE

* Work completed
    - Reviewed the Build (c482f08, diffed against 9706178) against plan units 1 to 6, preflight 3 resolutions A1 to A7, and brief acceptance criteria 1 to 6.
    - Re-ran the gates:
        - lint, format-check, REUSE and schema-docs-check pass.
        - JS 134/134.
        - pytest: 931 passed, 18 skipped. The only failure is the docs-lock test under local uv 0.8.22. It passes under CI's pinned uv 0.12.22, which QA checked.
    - Result (`.qa-validation-status`): `PASS`.
* Decisions made
    - No blocking findings. KISS, DRY, YAGNI, completeness, regression and integrity pass. The eight advisories are listed in `tasks.md` under "QA results".
* Insights
    - The cache-layout test can label a checkout as an installed plugin. That happens when a directory named `cache` sits exactly three levels above the computed plugin root, such as the Cursor localdev mirror of a repo cloned into `<x>/cache/stockroom`. QA reproduced it under dash, bash and busybox sh. It is unlikely and the damage is limited, so it is advisory only.

## 2026-10-16 - QA follow-up (minor fixes after QA PASS)

* Work completed
    - QA finding 1: a Cursor localdev mirror in a repo cloned directly into a directory named `cache` resolved as an installed plugin. Fixed test-first: the new case `test_localdev_mirror_in_a_cache_named_dir_is_dev` was red, then green. The real-install test now also requires the plugin layout `<root>/skills/sr-search`.
    - Finding 2: Step 7 now gives contributors `make shim`, `make shim TAKEOVER=1` for a dead foreign shim, and `make localdev` at the user's request for a live foreign one.
    - Finding 3: the `shim.py` `--help` action text and the `rectify` docstring summary mention replace-if-dead.
    - Finding 4: `systemPatterns.md` names MCP/LSP and the claude.ai-synced copies.
    - Finding 5: the troubleshooting last-resort install passes `--app-dir "$APP_DIR"`.
    - Finding 6: the dev gone-remedy wording now reads "go back to that install".
    - Findings 7 (zsh untested) and 8 (Clean Semantics untouched) were accepted as noted.
    - Affected modules: 90 passed, 15 skipped. Full pytest: 933 passed, 19 skipped, and 1 failure that is the known local-uv docs-lock check. Lint and format are clean.

## 2026-10-16 - REFLECT - COMPLETE

* Work completed
    - Wrote `reflection/reflection-plugin-root-resolution.md` and reconciled the persistent files: productContext and techContext skipped; systemPatterns was already updated.
* Insights
    - Plugin roots reach hooks, never agent shells, and Claude Code's skill substitution matches exact tokens only.
    - Marketplace copies carry `.git` and a `Makefile`, so the install layout, not checkout markers, distinguishes dev.
    - Keying the takeover on liveness removed the one stuck path out of dev.

## 2026-10-16 - POST-REFLECT - PR OPENED

* Work completed
    - Local uv upgraded to 0.12.22 via pipx, and `make ci` is fully green locally.
    - Draft PR #142 opened: "fix(shim): sr-initialize finds marketplace installs; dead shims heal at session start".

## 2026-10-16 - PR REVIEW TRIAGE - COMPLETE

* Work completed
    - Judged the 6 bot inline comments on PR #142 (4 from cursor[bot], 2 from coderabbitai[bot]) at the PR head 7f3917f. All 6 were reproduced in scratch: a checkout under a `synced/` folder or under a `cache/<a>/<b>/` shape gets labelled `claude` (2 comments raise the `synced` case); Step 7's mislabel row omits synced copies; `shim rectify` raises `PermissionError` on an uncheckable foreign engine dir (Python 3.11 to 3.13); the printed Step 2 line breaks on a path containing `'`.
* Decisions made
    - Every finding: fix in this PR. The operator said "fix all of those" and invoked `/niko-plan`.
* Insights
    - Labelling a copy `dev` by mistake fails safe, because Step 7 tells the agent to stop and ask when `APP_DIR` is not the user's checkout. Labelling a copy with a harness by mistake fails silently.
    - `Path.is_file()` handles errors differently by version: 3.11 to 3.13 raise on EACCES, 3.14 returns `False`.

## 2026-10-16 - PLAN (rework round 1: PR #142 review) - COMPLETE

* Work completed
    - Rewrote `tasks.md` for this round, keeping the operator decisions and evidence. There are 5 units: `_alive` counts an uncheckable engine as alive (executable); the Step 2 default-folder owner rule and a shell-safe printed line (executable); Step 7's synced row and an uncheckable-engine row (prose); `systemPatterns.md` and SumMem (prose); verification.
    - Prototyped the target Step 2 block in scratch: 13 modeled cases pass under dash and bash, and the quoted-path case also passes under busybox sh. Prototyped the target `_alive` on Python 3.11, 3.13 and 3.14: the same answers on all three.
    - Added acceptance criteria 7 to 9 to `projectbrief.md`.
* Decisions made
    - Agent decision, flagged: only a harness's default plugins folders are labelled automatically. An install-shaped copy elsewhere gets no owner, and the user decides. Substitution and `CURSOR_PLUGIN_ROOT` no longer decide the owner. The fallback is in `tasks.md`.
    - `_alive` stats `pyproject.toml` directly. Only ENOENT, ENOTDIR and ELOOP mean dead; any other `OSError` counts as alive.
    - The Step 2 tests read results back through the printed line, because that line is the agent's interface.
* Insights
    - Under `--plugin-dir`, `${CLAUDE_PLUGIN_ROOT}` substitution looks exactly like a real install's. It can never be the sole proof of an install.

## 2026-10-16 - PREFLIGHT - STOPPED (operator decision)

* Work completed
    - The first preflight attempt failed: Fable 5.1 was out of usage credits (HTTP 429). It changed nothing.
    - I stopped the retry on Opus before it finished, because the operator changed a requirement.
* Decisions made
    - Operator: "We do not want Cursor users to have to answer extra questions to account for Claude Code situations." Recorded in `activeContext.md`.

## 2026-10-16 - PLAN (rework round 1, revised for the Cursor decision) - COMPLETE

* Work completed
    - Revised `tasks.md`, `activeContext.md` and brief AC7 for the operator's decision that Cursor users get no Claude-driven questions.
    - Re-prototyped the Step 2 block with the `CURSOR_PLUGIN_ROOT` read kept: all 15 modeled cases pass under dash and bash, and the quoted path also passes under busybox sh.
* Decisions made
    - Outside default plugins folders: `CURSOR_PLUGIN_ROOT` holding this engine gives `cursor`, as in the first pass. Otherwise `OWNER` is empty: Claude Code asks the user, and other harnesses name themselves. The `${CLAUDE_PLUGIN_ROOT}` read is removed.
    - Test changes: `test_cursor_custom_cache_with_env` stays green unchanged; `test_leaked_cursor_root_is_ignored` now expects an empty owner.
    - Accepted residual: a Cursor checkout with a cache-shaped real path, read through that path and with no `CURSOR_PLUGIN_ROOT`, still gets `cursor`.

## 2026-10-16 - PREFLIGHT (rework round 1) - COMPLETE

* Work completed
    - Checked the revised rework plan (943395a) against `sr-initialize` SKILL.md, `stockroom.shim` and its template, `test_initialize_context.py`, `test_shim.py`, `scripts/localdev.sh`, the docs, and the six PR #142 inline comments.
    - Ran the target Step 2 block in scratch: 20 planned cases plus 5 extra probes, under dash, bash and busybox sh, reading results back through the printed line. All gave the planned results. Today's block fails exactly the five cases the plan names.
    - Ran the planned `_alive` against a mode-000 engine on Python 3.11, 3.13 and 3.14. It gives the planned results on all three. Today's code raises on 3.11 and 3.13 and overwrites the shim on 3.14, so the new tests go red on every version.
    - Result (first line of `.preflight-status`): `PASS WITH ADVISORY`.
* Decisions made
    - TDD encoding passes: Units 1 and 2 put their tests first, and Units 3 and 4 are prose. No strike or swap was needed.
* Insights
    - Advisories:
        - Step 7 needs a check command that reports errors, or its "cannot be checked" row is never reached.
        - The shim template, `localdev-status` and the `install` refusal wording still treat an uncheckable engine as missing or alive.
        - Add a `--takeover --force` → installed assertion.
        - The mislabel row misdescribes a cache-shaped checkout that the user labelled `dev`.
        - Cursor reads Claude's plugin copies, so a synced copy changes from `dev` to `claude` there.
        - AC1 and AC7 disagree.
        - Newline paths and EBADF are pathological.
    - Radical idea (advisory): the version folder proves the install. Claude names it after the manifest version, and Cursor after the clone's commit. That removes the Claude Code question and the Cursor residual.

## 2026-10-16 - BUILD (rework round 1: PR #142 review) - COMPLETE

* Work completed
    - Unit 1: `_alive` stats `pyproject.toml` directly. ENOENT, ENOTDIR and ELOOP mean dead; other `OSError` counts as alive. 2 new tests went red (`PermissionError`), then green.
    - Unit 2: new Step 2 block. It labels default plugins folders by path, keeps `CURSOR_PLUGIN_ROOT`, drops the `${CLAUDE_PLUGIN_ROOT}` read, and prints a shell-quoted line. `_run_block` now reads back through the printed line. 12 red (6 tests × sh/bash), then green.
    - Unit 3: Step 7 names its liveness check, adds a "cannot be checked" row, and widens the mislabel row to synced copies.
    - Unit 4: `systemPatterns.md` and two SumMem notes.
    - Unit 5: `make ci` green (pytest 944 passed, 23 skipped; JS 134/134; REUSE compliant). `claude plugin validate .` shows only the existing warning.
* Decisions made
    - Folded in preflight advisories 1 and 3 to 7. Advisory 2 was accepted as gaps. The version-folder idea is left for the operator.
* Insights
    - Reading results back through the printed line makes the agent's real interface the thing under test. It caught the `'` defect, which reading the block's own variables would have missed.

## 2026-10-16 - QA (rework round 1: PR #142 review) - COMPLETE

* Work completed
    - Compared the Build (a3f6a72, diffed against 4bfffbc) with plan units 1 to 5, the preflight dispositions, the six PR #142 inline comments, and brief acceptance criteria 1 to 9.
    - Re-ran the gates. `make ci` exited 0: JS 134/134, pytest 944 passed and 23 skipped, REUSE compliant. `claude plugin validate .` passed, with only the existing CLAUDE.md warning.
    - Probed AC8 beyond the tests: 10 unusual directory names under dash, bash and busybox sh. All 30 printed lines gave back the exact `APP_DIR` in a fresh shell.
    - Result (`.qa-validation-status`): `PASS`.
* Decisions made
    - No blocking findings. The six advisories are in `tasks.md` under "QA results, rework round 1".
* Insights
    - `_alive` now lets `ValueError` through: a NUL byte in a shim header raises, where `Path.is_file()` used to return `False`. Only a hand-corrupted shim can hold a NUL, so this is advisory.
