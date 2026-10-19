---
task_id: plugin-root-resolution
date: 2026-10-16
complexity_level: 2
---

# Reflection: plugin-root-resolution

## Summary

`sr-initialize` now finds the engine and shim owner without plugin-root environment variables. A marketplace install, meaning a harness cache copy or a claude.ai-synced copy, gets its harness label, and every checkout-based load gets `dev`. `shim rectify` now replaces a dead shim of any owner, so leaving dev never strands the on-path command. QA passed, and an end-to-end run on real Claude Code 2.1.301 confirmed the shipped text resolves correctly.

## Requirements vs Outcome

Every requirement was delivered.

- The hook audit found no fault, so the hooks are unchanged.
- Two additions came from the operator mid-plan: "contributors always get `dev`", and `rectify` replacing dead shims, which relaxed Constraint 4 with approval.
- Dropped by operator decision: option B (dev-load rectify no-op), option E (separate dev data), and the argument-substitution guards.
- Cursor's agent-shell behavior is still undocumented. The design does not depend on it, and a UAT line is left for the operator.

## Plan Accuracy

The first plan had the right diagnosis but the wrong owner rule. It labelled `claude --plugin-dir` as `claude`, and it relied on a `.claude`/`.cursor` path rule that misses `CLAUDE_CODE_PLUGIN_CACHE_DIR`. Three preflights and one operator round reshaped it:

- **Preflight 1:** the mirror path, and takeover offers on healthy shims.
- **Preflight 2:** `$N` / `$ARGUMENTS` substitution.
- **Operator:** dev semantics.
- **Preflight 3:** synced plugins, and Step 7 reading the shim off PATH.

The challenges that actually bit were layout facts: caches containing `.git` and `Makefile`, and `--plugin-dir` silently replacing the installed plugin. None of them was a technology risk.

## Build & QA Observations

The build was linear and clean: every unit went red, then green, and a mutation check confirmed the Step 2 test catches a regression to an unbraced token. `make ci` cannot pass end to end on this machine, because local uv 0.8.22 trips the lock checks. They pass under CI's pinned uv 0.12.22.

QA passed with one real edge case: a localdev mirror in a repo cloned into a directory named `cache` read as an installed plugin. It was fixed test-first by also requiring the `<root>/skills/sr-search` layout. Five wording and doc nits were fixed alongside.

## Insights

### Technical

- **Harnesses give plugin roots to hooks, never to agent shells.** For Claude Code, the only channel into a skill is skill-text substitution, and it matches exact tokens only. A bare `$CLAUDE_PLUGIN_ROOT` or `${…:-x}` stays literal, as do `$N` and `$ARGUMENTS` when arguments are passed. Check any skill shell snippet against this before trusting it.
- **Marketplace copies are git clones that include the `Makefile`,** so checkout markers cannot tell dev from installed. The install layout can: `…/cache/<marketplace>/<plugin>/<version>/skills/sr-search`. And "defer to `make shim` from the repo root" silently succeeds inside a plugin cache.
- **Ownership keyed on labels made the one stuck path.** "Never touch a foreign shim" also froze dead ones. Keying the takeover on liveness (no `pyproject.toml`) keeps the label as a courtesy for working shims only.
- **Executing a shipped skill fence in tests works.** Run it as a real program under each shell, with the harness rendering modeled exactly as a probe verified, and mutation-check it. This catches skill regressions that wording asserts cannot.

### Process

- **Agents silently improvising around a broken skill hid this bug from plugin 0.1.1 to 2.1.1.** Warehouse transcripts proved it in minutes. When a skill step "works", check what the agent actually ran.
- **A cheap headless `claude -p` probe** (small model, throwaway plugin, read the session transcript) settled substitution semantics that the docs left ambiguous. Two probes changed the design.
- **Asking "is this a real risk under the documented flow?"** before changing shared hook policy turned a proposed hook change (B) into a narrower fix that keeps dev self-heal. The operator's mental model of entering and leaving dev was the real spec.

### Million-Dollar Question

The engine already knows where it lives (`shim.default_app_dir()`). If "the owner is a function of where the engine is installed" had been foundational, one tested Python function would classify the install kind from the engine's own path. A real install is a harness cache or synced copy, with the harness taken from the path or a passed hint; everything else is `dev`. `shim install --owner auto`, `doctor probe` (including flagging a mis-owned shim), and a read-only `shim triage` for Step 7 would all call it. The skill would carry one line, handing over Claude Code's substituted root only as a hint for custom plugins roots.

What we built is that rule in shell inside SKILL.md, the one place a pre-shim agent can run it, pinned by tests. Moving it into the engine is the natural next step if the rule grows.

Follow-up candidates:

- `doctor probe` mis-owned-shim fact
- `stockroom shim triage`
- zsh in CI (macOS runner)
- operator UAT in Cursor for `CURSOR_PLUGIN_ROOT` in agent shells

---

# Rework round 1: PR #142 review fixes (2026-10-16)

## Summary

All six bot inline comments on PR #142 were valid and are fixed. Under `--plugin-dir`, no checkout is labelled `claude` because of where its path sits. Step 7 covers synced copies and engines that cannot be checked. `rectify` and `install` no longer raise on such engines. The printed Step 2 line is shell-quoted. QA PASS; `make ci` green (pytest 946 passed, 23 skipped).

## Requirements vs Outcome

All six findings were delivered, plus brief AC7 to AC9.

- The operator added one constraint after the first rework plan: no Claude-driven questions for Cursor users.
- So outside the default plugins folders only Claude Code asks; Cursor keeps its first-pass evidence (`CURSOR_PLUGIN_ROOT`).
- One Cursor outcome changes without a new question: a claude.ai-synced copy read from Cursor is now `claude`, not `dev`.
- Accepted residual: a Cursor checkout whose real path is cache-shaped still gets `cursor`.
- Deferred to the operator: preflight's idea of letting the version folder prove an install.

## Plan Accuracy

- The first rework plan broke a constraint nobody had stated: its cost line put a question on Cursor users. Because that line said so in plain words, the operator caught it before Build. One revision fixed it.
- Prototyping the Step 2 block before writing the plan held up: the red sets in Build matched the plan exactly.
- **Surprise:** Cursor agents on this machine read skills from Claude Code's plugin folders (25 reads in the warehouse). So a path rule written for Claude also decides Cursor outcomes.

## Build & QA Observations

- Build was linear: two executable units went red, then green, and one format-check line wrap was fixed.
- QA found a regression from this round: replacing `Path.is_file()` with a direct `stat` lost its `ValueError` catch, so a NUL byte in a header raised. It was fixed test-first after QA, together with four wording fixes.
- I filtered test-run output twice (`grep`, `sed`), which the test-running rules forbid. The summaries I read were complete, but the rule is about reading the whole output.

## Insights

### Technical

- **When replacing a stdlib convenience with the call underneath it, carry over every implicit catch.** `Path.is_file()` swallowed ENOENT-family errors and `ValueError`; listing the errnos covered only the first. Read the replaced function's `except` clauses, on every supported Python, before writing the replacement.
- **Judge a heuristic by which way it fails.** A wrong `dev` is caught, because Step 7 stops when `APP_DIR` is not the user's checkout. A wrong harness label is silent. Point uncertain branches toward the caught side.
- **Test the interface the agent consumes.** Reading results back through the printed line, not the block's variables, is what exposes quoting defects.

### Process

- **Put a plain-words cost line on every design choice in a plan.** It let the operator veto the Cursor question before any code was written.
- **Bots found four real path-shape edge cases that the first QA passed.** For path heuristics, QA should try hostile paths (`synced`, `cache/<a>/<b>`, quotes), as this round's QA did.

### Million-Dollar Question

This is still the first pass's answer: one engine-side classifier of the install kind. Preflight's version-folder proof sharpens it. Claude Code names the copy's folder after the manifest version and Cursor after the clone's commit, so the copy can prove it is an install without asking anyone or trusting substitution. That would remove the Claude Code question and the Cursor residual. It needs the operator's call, because it replaces a question they accepted.

---

# Rework round 2: Claude Code's install record (2026-10-16)

## Summary

Some copies are laid out like an install but sit outside the default plugins folders. For these, Step 2 now asks Claude Code's own install record first. If `installed_plugins.json` lists the copy's exact path, it gets `claude` with no question. Round 1's Claude Code question now reaches only copies the record does not list. QA PASS; `make ci` green (pytest 956 passed, 28 skipped).

## Requirements vs Outcome

- Delivered as planned. Brief AC7 was amended.
- Added: one Step 7 sentence. The agent skips the "is this your checkout?" question when the Step 2 block itself proved the owner.
- Out of reach by design, both falling back to the question: claude.ai-synced copies under a custom root (they have no record), and seed directories mounted away from the path they were built at.
- The version-folder proof stays rejected.

## Plan Accuracy

- The plan held exactly: the red set (8), the green run, and both mutants came out as predicted. That is because the target block was prototyped in a scratch copy of the repo before the plan was written.
- The surprise came during planning, not Build. For relative-path plugins in a local-path marketplace, Claude Code creates a cache entry and a record, but reads the plugin in place (`readFromFolder` in `claude plugin list --json`). So the record can name a folder the session never loads.
- I had first told the operator that such plugins are copied. The docs and the CLI corrected that before the plan relied on it.

## Build & QA Observations

- Build was linear.
- Preflight's advisory 1 reworded the Step 7 sentence: an owner the agent filled in itself is not proof.
- QA found no defects. Its one docstring note was fixed after QA.
- Both reviews pinned down an issue that predates this PR: Claude Code pastes the skill path into `SKILL_DIR="…"` unquoted, so a `"` in it stops the block, and a `$(` or backtick in it runs as a command.
- Fable 5.1 was out of credits (HTTP 429) both times, so preflight and QA ran on Opus.

## Insights

### Technical

- **Prefer the installer's own record to any path or naming heuristic.** Claude Code writes the record at install, moves it on update, and drops orphans from it. Match the exact quoted path string. That ignores nesting and indentation, and any escaping makes it miss rather than mislabel.
- **`installPath` is not always the folder a plugin loads from.** Check `readFromFolder`.
- **`CLAUDE_CONFIG_DIR` moves the plugins root too.** A rule keyed on `~/.claude/plugins/…` silently misses every user who sets it, and that group is larger than the `CLAUDE_CODE_PLUGIN_CACHE_DIR` one.

### Process

- **Test a premise live when the tests write both sides of it.** Here: is the path Claude Code substitutes the same string the record holds? One cheap headless session settled it before the plan was written.
- **Isolate probes of Claude Code plugins.**
    - For `claude plugin` CLI work, point `CLAUDE_CONFIG_DIR` at a scratch folder.
    - When a live session needs the real login, set `CLAUDE_CODE_PLUGIN_CACHE_DIR` and use `--scope local` in a scratch project.
    - Checksum the real records before and after.
- **Write probes as commented, self-checking script files (operator rule).** A mutation script that knows the expected failing set for each mutant gives a one-line verdict and never touches the worktree.
- **A "follow-up after this PR" needs a reason beyond tidy scope.** Here the PR itself introduced the question the follow-up removes, so the fix belonged in the PR.

### Million-Dollar Question

Still round 1's answer: one engine-side classifier, with an evidence order this round makes clear:

1. The harness's install record.
2. The default-folder path.
3. The harness's exported root.
4. Otherwise, ask.

Built from the start, `shim install --owner auto` would parse `installed_plugins.json` as JSON. Matching only the `installPath` key would remove the `projectPath` false match, and normalizing Windows paths would catch escaped ones. The skill would then carry one line.

Preflight's `${CLAUDE_PLUGIN_DATA}` idea could remove the question entirely: the data folder's id names the origin, `-inline` for `--plugin-dir` and `-<marketplace>` for an install. But a live probe must first show that Claude Code substitutes the token in skill text, and the operator has to decide.

Follow-up candidates:

- `SKILL_DIR="${CLAUDE_SKILL_DIR}"` lets the shell interpret `"`, `$`, backtick and `\` in the substituted path. This predates the PR, and only the user's own folder names can trigger it.
- Probe `${CLAUDE_PLUGIN_DATA}` substitution in skill text (operator decision).
- Carried over: `doctor probe` mis-owned-shim fact, `stockroom shim triage`, zsh in CI, Cursor UAT for `CURSOR_PLUGIN_ROOT`.

# Rework round 3: Claude Code's plugin data folder (2026-10-17)

## Summary

Step 2 now reads Claude Code's two pasted paths from a quoted heredoc. It uses the substituted `${CLAUDE_PLUGIN_DATA}` to settle the owner of an install-shaped copy outside the default plugins folders: a data folder in the copy's own plugins root gives `claude`, and `stockroom-inline` gives `dev`. In Claude Code, the question now arises only when the token is not substituted or the copy is outside the plugins root in use. QA PASS; `make ci` is green (pytest 974 passed, 37 skipped). A live check of the real `SKILL.md` on Claude Code 2.1.302 passed.

## Requirements vs Outcome

- **The operator's conditions are met:**
    - Every rule rests on the [loading reference](https://code.claude.com/docs/en/plugins/loading): the `@inline` origin, the reserved names, and `data/<plugin-id>` beside `cache/`.
    - When the signal fails, round 2's outcome applies, and an error line names the data folder (new AC10).
    - Hooks, `shim rectify` and the nightly job are unchanged.
    - No rule can give a wrong owner; the mutants show each rule's guard.
- **The quoting fix went in** because the same heredoc keeps `PLUGIN_DATA` from being read out of the environment. The `'` case still works. In Cursor, the path the agent fills in still goes through the shell (QA advisory 3), which is out of scope by operator decision.
- **Not helped:**
    - Native Windows: Git Bash's `pwd` prints `/c/…`, while the substituted data path is `C:/…`.
    - Seeds mounted elsewhere.
    - Synced copies under a custom root.

    All three fall back to round 2's outcome.
- **Added:** brief AC10, plus UC3 and AC3 updates (preflight advisory 2).

## Plan Accuracy

- The plan held. Both red sets (6 and 6), the green runs and all five mutants came out as predicted, once preflight corrected M3's set (it also catches the `--plugin-dir` case).
- Preflight had run the planned tests against today's block, the target and every mutant. That is why Build had no surprises.
- Preflight caught one wrong claim in the plan's narrative (native Windows) and one live-check detail: Claude Code does not load a copied plugin without its record, so the record can be moved aside only after the session.

## Build & QA Observations

- Build was linear. The BusyBox check and the mutation runner reused preflight's scripts.
- One process slip: a test run was piped through `tail`. It was re-run unfiltered at once.
- QA found no defects. It left three non-blocking advisories:
    - A cosmetic HOME mismatch in two tests.
    - The wording "(not given)" in the error line.
    - Cursor's agent-filled path is still parsed by the shell.
- The live check ran with no tools, `--max-turns 1`, hooks off (a canary hook proved it) and scratch plugins roots, and left real state unchanged. Its "Reached max turns (1)" exit is the intended stop.

## Insights

### Technical

- **Claude Code states a plugin's origin in the substituted data path**, `<plugins root>/data/<name>-<origin>`.
    - A whole-path match against the copy's own plugins root proves an install without reading the id.
    - The reserved `inline` origin proves a session plugin.
    - Neither rule can misfire, so a missing or changed token simply falls back.
- **Read harness-substituted text into a shell through a quoted heredoc.**
    - Double quotes still parse `$`, backticks and `"`.
    - Single quotes break on `'`, the one special character real folder names carry.
    - A quoted heredoc reads the bytes as written, and no environment variable can fill it.
    - Detect "not substituted" by the leading `$`. Never spell the whole token in the detection pattern, because the harness replaces it there too.
- **Claude Code's shell-form hooks expand `"${CLAUDE_PLUGIN_ROOT}"` from the environment**, not by pasting text (2.1.302 probe), so the hook files needed no change.

### Process

- **Ask what a failure must look like, and write the answer as an acceptance criterion.** The operator's two failure principles became AC10 and the mutant list. They also led to the shape of the design: each new rule only adds proof.
- **A live end-to-end check of the real artifact is cheap with the right locks:**
    - no tools, and one turn;
    - hooks off, proved by a canary;
    - scratch plugins roots;
    - checksums of the real records and shim.

  It closes round 2's "the tests write both sides of the premise" gap.
- **A preflight that runs the planned tests against prototyped variants makes Build predictable.** Reuse its scripts.

### Million-Dollar Question

Built this way from the start, Step 2 would take the owner from Claude Code's own statement of origin first, and use path rules only where nothing is substituted:

- `@inline` → `dev`.
- A marketplace or `@synced` origin whose copy sits in that plugins root → `claude`.
- Everything else falls through to the path rules.

Round 3's order is close to that. The install record remains as the fallback for reads with no substitution: a Cursor agent reading a Claude Code copy, or an older Claude Code.

The data token exists only in skill text, so the skill must at least capture it. The cleanest next form would pass both heredoc values to a tested, stdlib-only engine classifier (for example `stockroom shim classify --skill-dir … --plugin-data …`, run through `uv python find` as the hooks do). The rules would then live in Python tests instead of shell.

Follow-up candidates:

- Clearer error wording when no data folder was given (QA advisory 2).
- Cursor's agent-filled `SKILL_DIR="<…>"` is still shell-parsed (QA advisory 3; operator scope says no).
- Preflight's `PROOF` field idea (operator decision).
- Native Windows: compare Claude Code's own strings, deriving the root from `PLUGIN_DATA` and matching `SKILL_DIR`'s prefix, instead of `pwd` output (preflight advisory 3).
- For the PR text: a `--plugin-dir` session leaves an empty `data/stockroom-inline` folder (preflight advisory 6).
- Carried over: the `doctor probe` mis-owned-shim fact, `stockroom shim triage`, zsh in CI, and Cursor UAT.

# Rework round 4: paths with a space or `'`, and the nightly job's home (2026-10-18)

## Summary

A path that holds a space or `'` now works everywhere stockroom writes it into shell text. That covers the nightly cron and launchd entries, four Makefile recipes, `localdev.sh`'s hint and `doctor smoke`'s printed torch command; Step 2, the shim and both hooks already worked. The nightly entries also carry the stockroom home they were installed for, and `schedule status` reports entries that are out of date. QA passed on run 3, after two fixable failures. `make ci` is green (pytest 1008 passed, 38 skipped).

## Requirements vs Outcome

- **The operator's rule: fix what is common and breaking, everywhere.**
    - Inventory 1 lists every place a path meets shell text, with a result for a space and for `'`. The places that broke are fixed.
    - The rare characters (`$`, a backtick, `"`, `\`, `%`) are listed per place, not fixed.
    - The Cursor half of round 3's concern turned out to be safe already for the common characters, because the path sits in double quotes. A guard test now pins it.
- **QA follow-up 1 from round 3 is done.** The error line says "nothing proves who installed it", which holds in every harness. When a data folder was given, the line names it and where it was expected.
- **Added, from preflight:**
    - The nightly job never received `STOCKROOM_HOME` or `XDG_DATA_HOME`. Every custom-home user's job has filled the default warehouse since scheduling shipped.
    - Both entries now carry the resolved home (AC12). Inventory 2 records every variable the engine reads, and why `XDG_CONFIG_HOME` and the one-shot source overrides are not carried.
- **Added so the fix reaches existing users:**
    - `status` reports `up-to-date:` and `entry home:`.
    - Step 8 offers a consented re-install of an out-of-date entry.
    - Users who never re-run `sr-initialize` keep their old entry; that goes in the PR text.
- **Added from QA:** `doctor smoke`'s printed command, the Step 8 `unreadable` clause, and the odd-home status guard.

## Plan Accuracy

- **The first plan's premise was wrong.** It fixed the shell parsing, and preflight then asked what the engine sees when the job runs. For the users the plan named, the quoting-only fix would have turned a job that fails visibly into one that silently writes to the wrong warehouse.
- **Inventory 1 defined "instance" by code shape** (code that runs a shell). It missed a command stockroom prints for the agent to run. QA run 1 found it with a search over printed messages.
- **Rerun 1 left an older assertion behind** that expected the unquoted path. It passes here and in CI, and fails only from a checkout whose path is odd. QA run 2 found it by running the whole suite from `Jane Doe` and `O'Brien` copies.
- **Mutant counts shifted twice as tests grew stronger:** M5 and M6 at 5, M3 and M4 at 4. Both times there were more red tests, never fewer. The predictions were corrected, and the runs repeated.

## Build & QA Observations

- Each executable unit went red, then green, as predicted.
- The Make test, a stub `uv` with a call count, caught the case where `make shim` exits 0 having run nothing.
- **Three QA runs.** The two failures were small, and both were completeness gaps in this round's own bug class, not defects in what was built.
- **Process slips, each fixed before it mattered:**
    - a dropped `def` line while adding a stub;
    - a probe script with dead lines, rewritten before it ran;
    - a mutation run with stale predictions.

## Insights

### Technical

- **Neither cron nor launchd loads a shell profile.** An unattended job sees only what its entry carries. Any setting the engine reads from the environment silently falls back to its default there. That is a wrong warehouse, not an error.
- **A fix to a generated artifact reaches existing users only when something re-renders it.** Status that compares the installed artifact with the current rendering, plus a consented re-install, is the cheap way to reach them.
- **`shlex.quote` leaves a string of safe characters unchanged.** So a quoting fix renders byte for byte as before in the common case, and existing exact-match tests stay green.
- **Two `'` on one shell line pair up.** In a Makefile recipe, a path with one `'` used in two places can turn the whole command into a variable assignment that exits 0 and runs nothing. Count the calls; do not trust the exit status.

### Process

- **Define an "instance" by what a user or agent meets, not by code shape.** "Paths in shell text" includes text printed for someone else to run. Search messages as well as code that runs a shell.
- **When a fix targets odd paths, run the test suite itself from such a path.** A copy of the repo under `Jane Doe` and `O'Brien` is cheap. It needs `git init` plus `git add -A`, or the comparison against a `plain` copy, because of the `reuse` test (SumMem note).
- **For an unattended process, ask what it sees when it runs:** its environment, its working folder, its PATH. Do not stop at how its text is parsed. That question produced this round's most important fix.

### Million-Dollar Question

If "every `stockroom` run resolves the same home and engine, however it was started" had been a foundational assumption:

- **The shim would bake the home** the same way it bakes `APP_DIR`, as `STOCKROOM_HOME="${STOCKROOM_HOME:-<baked>}"`. The cron entry, a launchd job, a Cursor opened from the Dock and an interactive shell would then all agree, and no entry would need to carry the home.
- **The scheduler entry would be one simple command with no inner shell,** such as preflight's `stockroom schedule run`, with the log written by Python. launchd would get a plain argument vector, and cron one quoted word.
- **Every printed or generated command would go through one helper** (`shlex.join`). Quoting would then be structural rather than remembered per call site.

Round 4's fixes are compatible with that shape. They carry the home in the entry rather than in the shim, which keeps this round's change within the scheduler and leaves the shim contract unchanged.

Follow-up candidates:

- Bake the home into the shim, and add `stockroom schedule run` (the shape above).
- QA run 1 advisories 3 to 5:
    - the Make test accepts an empty `PYTHONPATH` (fixed after Reflect, from CodeRabbit review 5565466269: each uv call's `PYTHONPATH` and `--app-dir` are now pinned);
    - `up-to-date` depends on where the shell finds `uv`;
    - zsh never runs, there is no live cron or launchd run, and `<build>` stays a placeholder.
- A CI job, or a `make` target, that runs the suite from a checkout path holding a space and `'`.
- For the PR text:
    - custom-home users' nightly jobs have used the default warehouse; re-run `sr-initialize`, or `stockroom schedule install --time HH:MM` (without `--time` it resets to 03:30);
    - the empty `data/stockroom-inline` folder.
- Carried over:
    - preflight's `PROOF` idea;
    - native Windows;
    - the `doctor probe` mis-owned-shim fact;
    - `stockroom shim triage`;
    - Cursor UAT, including whether Cursor pastes `${CURSOR_PLUGIN_ROOT}` into its hooks as text.
