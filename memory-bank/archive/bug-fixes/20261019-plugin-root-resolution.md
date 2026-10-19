---
task_id: plugin-root-resolution
complexity_level: 2
date: 2026-10-19
status: completed
---

# TASK ARCHIVE: plugin-root-resolution

## SUMMARY

From plugin 0.1.1 to 2.1.1, `sr-initialize` Step 2 read `CLAUDE_PLUGIN_ROOT` and `CURSOR_PLUGIN_ROOT` from the agent's shell. Neither harness puts them there, so a marketplace install fell through to the "dev checkout" path. Agents improvised around it silently, which left users with a wrong-owner shim or no shim. Warehouse transcripts proved the bug in minutes.

Step 2 now resolves the engine and the shim owner without those variables:

- `APP_DIR` is this skill's sibling `sr-search` folder.
- A marketplace install (a harness cache copy, or a claude.ai-synced copy) gets its harness label.
- Every checkout-based load gets `dev`.

`shim rectify` now replaces a dead shim of any owner, so leaving dev never strands the on-path command.

Pull request [#142](https://github.com/Texarkanine/stockroom/pull/142) went through a first pass and four rework rounds:

1. Review fixes:
    - no checkout is labelled `claude` because of where its path sits;
    - Step 7 covers synced copies and engines that cannot be checked;
    - `rectify` and `install` never raise on such engines;
    - the printed Step 2 line is shell-quoted.
2. Claude Code's install record (`installed_plugins.json`) proves an install that sits outside the default plugins folders.
3. Claude Code's substituted `${CLAUDE_PLUGIN_DATA}` settles the owner. Step 2 reads the pasted paths through a quoted heredoc.
4. A path with a space or `'` now works everywhere stockroom writes it into shell text. The nightly cron and launchd entries also carry the stockroom home they were installed for, and `schedule status` reports out-of-date entries.

A last fix after Reflect, from CodeRabbit review 5565466269, pins each uv call's `PYTHONPATH` and `--app-dir` in the Make path test (ca095d9).

## REQUIREMENTS

User story: a user who installs stockroom from a marketplace (Claude Code or Cursor) wants `sr-initialize` and the session-start hooks to find the installed engine and the right shim owner on their own.

Use cases:
- **Claude Code marketplace install:** `sr-initialize` often runs in the same session, before any SessionStart hook has fired.
- **Cursor marketplace install:** the fix must not break Cursor's path.
- **Dev checkout or localdev mirror:** contributors always get `dev`. That covers `claude --plugin-dir`, Cursor `plugins/local`, local-path marketplaces loaded in place, and the Cursor mirror.
- **Leaving dev:** run `make localdev-clean`, or delete the checkout. The next installed session restores a working shim either way.

Requirements:
1. Rebuild the model of where `CLAUDE_PLUGIN_ROOT` reaches, from the Claude Code docs.
2. Do the same for `CURSOR_PLUGIN_ROOT`, recording what stays unknown.
3. Fix detection, so that each harness's install resolves by a documented mechanism.
4. Audit both hook files, changing them only for a real fault.
5. Correct docs and comments that state the wrong model.
6. Pin the detection contract in tests.

Constraints:
- One shared `SKILL.md` serves both harnesses, with no build step.
- The session hook stays idempotent and never errors.
- TDD.
- The shim policy changes in exactly one approved way: `rectify` replaces a dead shim of any owner.
- No separate dev data.

Acceptance criteria. AC1 to AC6 are the original; AC7 to AC12 were added in review and rework rounds 3 and 4:
1. A Claude Code install in the default plugins folder gets `OWNER=claude` and the plugin-cache `skills/sr-search` path.
2. A Cursor install gets `OWNER=cursor` by a documented or verified mechanism, or the uncertainty is stated and does not misroute the user.
3. Every checkout-based load gets `dev`, including a `--plugin-dir` checkout at a cache-shaped path, which Claude Code's `stockroom-inline` data folder identifies. A copy inside the active plugins root's own `cache/` gets `claude`. A cache-shaped checkout with no data folder, outside the default folders, makes Claude Code ask. Cursor names `cursor` there, an accepted residual. Re-running `sr-initialize` never offers to take over a shim its owner still maintains.
4. A dead `dev` shim is replaced at the next installed session start. A live foreign shim is never touched.
5. No doc claims that plugin-root variables reach agent shells.
6. `make ci` passes.
7. A path labels a copy only inside a default plugins folder (`…/.claude/plugins/cache/…`, `…/.claude/plugins/synced/…` or `…/.cursor/plugins/cache/…`). Outside those folders:
    - the data folder in the copy's own plugins root, or an exact `installed_plugins.json` entry, gives `claude`;
    - `stockroom-inline` gives `dev`;
    - otherwise Claude Code asks.

    Cursor users get no new question (operator decision).
8. The printed Step 2 line is valid shell for any newline-free path, including `'` and spaces.
9. `shim rectify` exits 0 and leaves the shim alone when a foreign engine cannot be checked. `shim install` refuses such a shim without `--takeover --force`. Neither command raises.
10. When the data folder is missing or moved, Step 2 falls back to the install record, then to the question, with an error line that names the data folder. It never produces a wrong owner, so nothing reaches the hooks, `rectify` or the nightly job.
11. A space or `'` in a path works everywhere stockroom writes it into shell text:
    - the Step 2 block, Steps 3 to 7, the shim and both hooks (already true);
    - the nightly cron and launchd entries;
    - the Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` recipes;
    - `localdev.sh`'s printed hint;
    - `doctor smoke`'s printed torch command.

    `$`, a backtick, `"`, `\` and `%` are out of scope (operator decision).
12. The nightly job runs against its install home. `schedule status` reports drift and the home an entry carries, and `sr-initialize` offers a consented re-install.

## IMPLEMENTATION

**How Claude Code delivers the plugin paths.** Harnesses give plugin roots to hooks, never to agent shells. The only channel into a Claude Code skill is skill-text substitution, and it replaces exact tokens only: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_DATA}`, plus `$N` and `$ARGUMENTS` when the skill gets arguments. A bare `$CLAUDE_PLUGIN_ROOT`, or a form like `${…:-x}`, stays literal. Step 2 reads those paths from a quoted heredoc. That reads the bytes as written, and no environment variable can fill it. "Not substituted" is detected by the leading `$`; the whole token is never spelled out in the detection pattern, because the harness would replace it there too.

**Owner evidence order in Step 2:**
- default-folder path layout `…/cache/<marketplace>/<plugin>/<version>/skills/sr-search`, also requiring the `<root>/skills/sr-search` layout (QA's `cache`-named-clone case);
- Claude Code's data folder: `<plugins root>/data/<id>` beside the copy's own `cache/` → `claude`, and `stockroom-inline` → `dev`;
- an exact quoted-path match in `installed_plugins.json` → `claude`;
- the `${CURSOR_PLUGIN_ROOT}` placeholder that a Cursor agent fills in → `cursor`;
- otherwise, in Claude Code only, the question.

An install-shaped copy with nothing to prove its owner prints "… nothing proves who installed it". When a data folder was given, the line also names it and the folder it was expected in.

**Step 7** sorts an existing shim by its header owner and its baked dir. It offers a consented takeover only for a dead foreign shim, or for a `dev` shim baked inside a harness plugins tree. It skips the "is this your checkout?" question when Step 2 proved the owner.

**`stockroom.shim`:**
- `rectify` keys takeover on liveness (no `pyproject.toml` in the baked dir), not on the label.
- An engine dir that cannot be checked is a no-op for `rectify` and a refusal for `install`. The code catches every implicit `Path.is_file()` error, including `ValueError` for a NUL byte.
- The `dev` missing-dir remedy points to starting a session of an installed harness plugin.

**`stockroom.schedule` (round 4):**
- Every path in an entry goes through `shlex.quote`.
- `_cron_entry` renders `PATH=… STOCKROOM_HOME=… /bin/sh -c '<payload>'`.
- `_launchd_job` puts `STOCKROOM_HOME` in `EnvironmentVariables`.
- `cron_status` and `launchd_status` report `up-to-date: yes|no|unknown` and `entry home: <home>|not set|unreadable`.
- Step 8 offers `stockroom schedule install --time HH:MM`, with consent only.

**Other files:**
- The Makefile recipes double-quote `$(CURDIR)` paths.
- `localdev.sh` double-quotes its hint.
- `doctor.py` quotes the `--directory` path in its printed command.
- The hook files are unchanged. Claude Code's shell-form hooks expand `"${CLAUDE_PLUGIN_ROOT}"` from the environment (2.1.302 probe).

Key files:
- `skills/sr-initialize/SKILL.md`
- `skills/sr-search/src/stockroom/shim.py` and `shim_template.sh`
- `skills/sr-search/src/stockroom/schedule.py`
- `skills/sr-search/src/stockroom/doctor.py`
- `Makefile` and `scripts/localdev.sh`
- the tests: `test_initialize_context.py` (new), `test_contributor_paths.py` (new), `test_schedule.py`, `test_shim.py`, `test_doctor.py`
- the docs: `docs/architecture/packaging.md`, `docs/contributing/preparation.md`, `docs/user-guide/load/schedule.md`, `docs/user-guide/troubleshooting/index.md`
- `memory-bank/systemPatterns.md`, which gained the scheduler-environment sentence and the section "Paths in shell text are quoted"

## TESTING

- **`test_initialize_context.py`** runs the shipped Step 2 fence as a real program under dash, bash and zsh (zsh skips when it is absent), with each harness's rendering modeled exactly as live probes verified. Results are read back through the printed line, which is how quoting defects surface. BusyBox sh checks passed 5/5 in each round that touched the block.
- **Mutation checks**, on `git archive` copies with poison stand-ins for uv, crontab and launchctl, ran in every round. Each mutant turned red exactly its predicted set:
    - round 4: M1 to M10, ALL OK;
    - the CodeRabbit fix: four dropped-argument mutants, all caught, which the old assertions all passed.
- **Preflight** ran on the first pass, three times (FAIL, FAIL, PASS WITH ADVISORY), and on every round. Round 4's first run was FAIL (fixable): the nightly job lacked `STOCKROOM_HOME`. The second run was PASS WITH ADVISORY; its advisories added `entry home:`, the troubleshooting line and `--time HH:MM`. Preflights ran the planned tests against prototyped targets and mutants, which made Build predictable.
- **QA PASS** on every round. Round 4 took three runs:
    - run 1 found `doctor smoke`'s unquoted printed command;
    - run 2 ran the whole suite from `Jane Doe` and `O'Brien` checkouts and found an older assertion that expected the unquoted path;
    - run 3 passed.
- **Live checks:**
    - an end-to-end run on Claude Code 2.1.301 (first pass);
    - a run of the real `SKILL.md` on 2.1.302 (round 3), with no tools, one turn, hooks off (proved by a canary), scratch plugins roots, and checksums of the real records and shim.
- **Final `make ci`** (2026-10-19, after ca095d9) is green: ruff, format, schema docs, JS 134/134, pytest 1008 passed and 38 skipped, and REUSE compliant. `claude plugin validate .` passes.
- **Not run:** a live cron or launchd job, a macOS machine, zsh, and Cursor UAT.

## LESSONS LEARNED

### Technical

- **The skill was the broken surface, not the hooks.** Check every skill shell snippet against the exact-token substitution rule, because an agent will silently improvise around a broken step.
- **Marketplace copies are git clones that include the Makefile.** Checkout markers cannot tell dev from installed, and `make shim` "succeeds" inside a plugin cache. The install layout, the data-folder origin and the install record can tell them apart.
- **Prefer the installer's own statements to path heuristics.**
    - Claude Code names a plugin's origin in `<plugins root>/data/<name>-<origin>`, with the reserved `inline` origin for a session plugin.
    - `installed_plugins.json` follows installs, updates and orphans.
    - `installPath` is not always the load folder; check `readFromFolder`.
    - `CLAUDE_CONFIG_DIR` and `CLAUDE_CODE_PLUGIN_CACHE_DIR` both move the plugins root.
- **Ownership keyed on labels froze dead shims.** Key takeover on liveness, and keep the label as a courtesy for live shims only.
- **Judge a heuristic by which way it fails.** A wrong `dev` is caught by Step 7. A wrong harness label is silent. Point uncertain branches toward the caught side.
- **When replacing a stdlib convenience with the call underneath it, carry over every implicit catch it had.**
- **Neither cron nor launchd loads a shell profile.** An unattended job sees only what its entry carries, so an unset `STOCKROOM_HOME` meant a wrong warehouse, not an error. A fix to a generated artifact reaches existing users only when something re-renders it, so status drift reporting plus a consented re-install is the cheap way to reach them.
- **`shlex.quote` leaves a string of safe characters unchanged,** so quoting fixes render byte for byte as before in the common case.
- **Two `'` on one Make recipe line pair up** and can turn the command into a variable assignment that exits 0 and runs nothing. Count the calls, and pin each call's arguments exactly.

### Process

- **Settle ambiguous harness semantics with live probes:** a cheap headless `claude -p` with a small model and a throwaway plugin, isolated with `CLAUDE_CONFIG_DIR` or `CLAUDE_CODE_PLUGIN_CACHE_DIR`, with the real records checksummed before and after. Test a premise live when the tests write both sides of it.
- **Put a plain-words cost line on every design choice in a plan.** It let the operator veto a Cursor question before any code was written.
- **Ask what a failure must look like, and write it as an acceptance criterion** (AC10).
- **Define a bug class by what a user or agent meets, including printed commands,** not by code shape.
- **For unattended processes, ask what they see when they run.**
- **When a fix targets odd paths, run the suite from such a path.** In a `git archive` copy, use `git init` plus `git add -A`, or the `reuse` test scans the untracked `.venv`.
- **Bots found real path-shape edges after QA passed.** QA for path heuristics should try hostile paths.
- **Process slips, all fixed before they mattered:**
    - test output was filtered several times, against the test-running rule (each time the whole output was then read, or the run repeated unfiltered);
    - a dropped `def` line while adding a stub;
    - stale mutant predictions.

### Million-Dollar Question

If "the owner is a function of where the engine is installed" and "every `stockroom` run resolves the same home and engine" had been foundational, the design would look like this:

- **One tested, stdlib-only engine classifier** would take Claude Code's substituted values as hints, in the order: origin from the data folder, install record, default-folder path, exported root, then ask. `shim install --owner auto`, `doctor probe` and a `shim triage` verb would all call it, and the skill would carry one line.
- **The shim would bake the home** as it bakes `APP_DIR`.
- **The scheduler entry would be a plain `stockroom schedule run`.**
- **Every printed command would go through `shlex.join`.**

The shipped fixes are compatible with that shape.

## PROCESS IMPROVEMENTS

- A preflight that runs the planned tests against prototyped targets and every mutant made each Build linear. Keep doing it.
- Commented, self-checking mutation scripts that know each mutant's expected red set gave one-line verdicts and never touched the worktree. This is the operator's rule, and it should be the default.
- QA round 4's odd-checkout suite run should become a CI job or a `make` target, so it is not left to memory.

## TECHNICAL IMPROVEMENTS

- Move the Step 2 owner rules into an engine classifier, for example `stockroom shim classify --skill-dir … --plugin-data …`, run the way the hooks run Python. The rules would then live in Python tests instead of shell.
- Bake `STOCKROOM_HOME` into the shim, and add `stockroom schedule run` so the cron and launchd entries need no inner shell.
- Route printed and generated commands through one `shlex.join` helper.
- Preflight's idea: let `shim rectify` call a never-raising `schedule heal` that re-renders an entry when its home and time match the session's own resolution. That would reach users who never re-run `sr-initialize`. It needs an operator consent decision.

## NEXT STEPS

- **Finish PR #142.** The PR text should say:
    - custom-home users' nightly jobs have filled the default warehouse since scheduling shipped; they should re-run `sr-initialize`, or `stockroom schedule install --time HH:MM` (without `--time` it resets to 03:30);
    - a `--plugin-dir` session leaves an empty `data/stockroom-inline` folder.
- **Open follow-ups:**
    - `up-to-date` depends on where the shell finds `uv`;
    - zsh, a live cron or launchd run, and the `<build>` placeholder;
    - native Windows: Git Bash prints `pwd` as `/c/…` while the data path is `C:/…`, so compare Claude Code's own strings instead;
    - Cursor UAT: does `CURSOR_PLUGIN_ROOT` reach agent shells, and does Cursor paste `${CURSOR_PLUGIN_ROOT}` into hooks as text;
    - Cursor's agent-filled `SKILL_DIR` is still shell-parsed for rare characters;
    - preflight's `PROOF` field idea;
    - the `doctor probe` mis-owned-shim fact;
    - `stockroom shim triage`.
