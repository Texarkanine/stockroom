# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

**Rework round 4: paths with a space or `'` work wherever stockroom writes them into shell text.** Rounds 1 to 3 are complete through Reflect on this branch. Round 3's plan, with its build and QA records, is in git at 0e458e9 (`memory-bank/active/tasks.md`). The history of all rounds is in `progress.md`.

Round 3 read Claude Code's pasted paths from a quoted heredoc, which fixed one place a path meets a shell. The operator then asked for every such place. This round inventories them all and fixes each one where a common character, a space or `'`, breaks it. Four places break:

- **The nightly job.** Under cron, a stockroom home or shim folder with a space fails every night with exit 127 and writes no log. A `'` makes `stockroom schedule install` raise `AssertionError`. Under launchd, both characters give a shell syntax error every night. Nobody is watching when this happens.
- **The Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` recipes.** A checkout path with a space fails. With a `'`, `make shim` exits 0 and runs nothing, because the two `'` on that recipe line pair up and the whole command becomes one variable assignment. Step 7 of `sr-initialize` sends contributors to `make shim`.
- **`localdev.sh`'s Claude hint.** It prints `claude --plugin-dir <checkout>` unquoted, so the command a contributor copies splits at the space.
- **QA follow-up 1 from round 3.** This one is wording, not quoting. Step 2's error line says "the plugin data folder (not given)" when nothing was substituted. In Cursor, that names a Claude Code idea.

Who it helps:

- Users whose stockroom home, `XDG_DATA_HOME`, `HOME` or `~/.local/bin` path holds a space or `'`. Examples are `~/Library/Application Support` on macOS, or a Windows profile such as `/mnt/c/Users/Jane Doe` under WSL. Their nightly job starts working.
- Contributors whose checkout path holds a space or `'`.

Cursor users get no new questions. Their Step 2 path already works with both characters, and this round adds a test that keeps it that way.

### Operator decisions (2026-10-18)

- **Fix what is both common and breaking.** The operator: "Let's fix things that are both common and breaking. so, "space in path," yeah. "if someone puts cryllic diacritics in-between 4 special shell characters in their homedir," no."
  - In scope: a space or `'` in any path stockroom writes into shell text.
  - Out of scope: `$`, a backtick, `"`, `\` and `%` in folder names. Where those still break, the inventory lists them instead of fixing them.
- **Fix every instance, not one.** The operator objected that round 3 "just fixed 1 frickin place". So the inventory below covers every place stockroom writes a path into shell text, and gives a result for each.
- Earlier decisions stand (round 3's plan, at 0e458e9): the failure principles (brief AC10), contributors always get `dev`, hooks stay as they are, and no Claude-driven questions for Cursor users.

### Inventory: every place stockroom writes a path into shell text

How it was built:

- A search of all tracked code, scripts, hooks and skill files outside `docs/` and the tests, for shell runs (`shell=True`, `os.system`, `sh -c`, `subprocess`, `shlex`).
- A read of every bash fence in every `SKILL.md` and skill reference.
- A read of the Makefile, `scripts/localdev.sh`, both hook files and the shim template.
- Probes with spaces and `'`, listed under Evidence.

| Where | Who writes the path | Space | `'` | This round |
| --- | --- | --- | --- | --- |
| Step 2, Claude Code's pasted paths (quoted heredoc) | Claude Code | works | works | none (round 3) |
| Step 2, Cursor's placeholder `SKILL_DIR="<…>"` | the agent | works (inside `"…"`) | works | guard test (Unit 3) |
| Step 2's printed line `APP_DIR='…'` | the block | works | works (AC8) | none |
| Steps 3 to 7: `"$APP_DIR"`, `--app-dir "$APP_DIR"` | the printed line | works | works | none |
| Step 7, `ls -dL -- "<STOCKROOM_APP_DIR>/pyproject.toml"` | the agent, from the shim header | works (inside `"…"`) | works | none |
| Step 7, `grep … ~/.local/bin/stockroom` | the shell (`~`) | works (tilde results are not split) | works | none |
| The shim (`APP_DIR=` via `shlex.quote`, then `"$APP_DIR"`) | the engine | works | works | none |
| The Claude Code hook (`"${CLAUDE_PLUGIN_ROOT}"`, expanded from the environment) | Claude Code | works | works | none |
| The Cursor hooks (`"${CURSOR_PLUGIN_ROOT}"`, double-quoted either way) | Cursor | works | works | none |
| The cron entry: the log path and the `PATH=` value | the engine | **breaks**: exit 127 every night, no log | **breaks**: `schedule install` raises `AssertionError` | Unit 1 |
| The launchd payload: the log path | the engine | **breaks**: syntax error every night | **breaks**: syntax error every night | Unit 1 |
| Makefile `shim`, `torch`, `local-engine`, `local-dashboard` | `$(CURDIR)` | **breaks**: exit 2 or 127 | **breaks**: syntax error, or `make shim` exits 0 having run nothing | Unit 2 |
| `localdev.sh`'s printed `claude --plugin-dir …` hint | the script | **breaks** when copied | **breaks** when copied | Unit 2 |
| `localdev.sh`, every other path | the script | works (all quoted) | works | none |
| Other skills' fences (`sr-query`, `sr-semantic`, `sr-dashboard`, cookbook) | none | no paths | no paths | none |
| Engine subprocess calls (`doctor`, `engine_env`, `torch_source`, `dashboard`, `shim`) | the engine | argv lists, no shell | same | none |
| `launchd`'s `EnvironmentVariables`, `StandardOutPath` and `StandardErrorPath` | the engine | plist values, no shell | same | none |

Out of scope, and still breaking for the rare characters (operator decision):

- The Step 2 placeholder and the Step 7 typed path, for `$`, a backtick, `"` or `\`.
- The Cursor hooks for the same characters, if Cursor pastes its root in as text. Whether it does is unverified.
- `%` anywhere in a cron entry (cron reads `%` as a newline).
- The docs' example commands, which are placeholders for a person to fill in.

The scheduler fix also handles `$`, a backtick and `"`, because `shlex.quote` covers every character. The probe shows that for `$x`.

### Evidence that shaped the plan

- **Scheduler, today vs planned** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/schedule_fix_probe.py`).
  - Setup: the stockroom home and a fake `stockroom` shim both sit under a folder named `plain`, `Jane Doe`, `O'Brien` or `cost$x`.
  - It runs the cron command part as cron does (`<shell> -c <command>`) and the launchd `ProgramArguments` as launchd does, under dash, bash and BusyBox sh.
  - Today: 18 of the 18 non-plain cases fail.
    - Space: cron exits 127 ("Doe/bin:/usr/bin:/bin: not found"), and launchd exits 2 (syntax error).
    - `'`: cron rendering raises `AssertionError`, and launchd exits 2 ("Unterminated quoted string").
    - `$x`: the log cannot be created.
  - Planned (`shlex.quote` on the log path, the `PATH=` value and the whole payload): all 24 cases pass.
- **Makefile, today vs planned** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/make_quoting_probe.sh`).
  - Setup: the Makefile alone is copied into `<tmp>/<name>/stockroom/`. Each target runs with `UV=<fake uv>`, which records `PYTHONPATH` and its arguments and runs nothing.
  - Today: plain passes, and 8 of 8 space and `'` cases fail.
    - The `'` `shim` case is the silent one: exit 0 with no `uv` call.
  - Planned (`"$(CURDIR)/$(ENGINE)/src"` and `--app-dir "$(CURDIR)/$(ENGINE)"`): 12 of 12 pass. That counts the expected `uv` calls and checks every `--app-dir` and `PYTHONPATH` value.
- **The planned Step 2 error line** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/error_line_probe.sh`).
  - dash, bash and BusyBox sh print the same two messages, for paths holding a space and `'`.
  - zsh is not installed here (carried).
- **Documented behavior the tests model:**
  - cron runs "the entire command portion of the line, up to a newline or % character" with `/bin/sh` ([crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html)).
  - launchd runs `ProgramArguments` as an argument vector, without a shell ([launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html)).
  - `shlex.quote` returns "a shell-escaped version of the string", safe as one token for a POSIX shell, and leaves strings of safe characters unchanged ([Python docs](https://docs.python.org/3/library/shlex.html#shlex.quote)).

### Target design

**`stockroom.schedule`** (`import shlex`):

```python
payload = f"(date; stockroom ingest && stockroom embed) >> {shlex.quote(str(_log_path(home)))} 2>&1"
...
def _sh_wrap(payload: str) -> str:
    return f"/bin/sh -c {shlex.quote(payload)}"
...
entry = f"{minute} {hour} * * * PATH={shlex.quote(path_prefix)} {_sh_wrap(render_payload(home))}"
```

- launchd keeps `["/bin/sh", "-c", payload]`. The payload's quoted log path is parsed once, by that shell. `EnvironmentVariables` and the two log keys stay raw, because launchd reads them as plist values, not as shell text.
- `shlex.quote` leaves a path of safe characters unchanged. So for the common case the rendered entry is byte for byte what it is today, and every existing test stays as it is.
- The `'` assert in `_sh_wrap` goes, because `shlex.quote` handles `'`. The `%` assert in `render_payload` stays (`%` is out of scope).

**Makefile:** in the `torch`, `shim`, `local-engine` and `local-dashboard` recipes, `PYTHONPATH="$(CURDIR)/$(ENGINE)/src"` and `--app-dir "$(CURDIR)/$(ENGINE)"`.

**`localdev.sh`:** ``use `claude --plugin-dir \"${sc_root}\"` for a session-scoped plugin load``.

**Step 2's error line** (replaces the `else printf` line of the `*)` arm):

```bash
      else printf 'sr-initialize: %s is laid out like an installed plugin outside the default plugins folders, and no install record lists it%s\n' "$APP_DIR" "${PLUGIN_DATA:+; its plugin data folder $PLUGIN_DATA is not in ${CACHE_DIR%/*}/data}" >&2
```

- With no data folder, it names only the copy, with no Claude Code idea in it.
- With a data folder, it names the folder and where it was expected.

## Test Plan (TDD)

### Behaviors to Verify

**Unit 1: the nightly entries run for homes with a space or `'`** (`test_schedule.py`).

Each case builds `<tmp>/<folder>/stockroom-home` and `<tmp>/<folder>/bin/stockroom`. The shim is a fake that appends `fake stockroom <args>` to stdout. So both the log path and the `PATH=` value hold the folder name. Folders, parametrized: `plain`, `Jane Doe`, `O'Brien` (ids `plain`, `space`, `apostrophe`).

- **Cron.** Install through `cron_install` with `FakeCrontab` and a `which` that finds the fake shim, and no `uv`. Take the entry's command part (after the five time fields) and run it as cron does: `/bin/sh -c <command part>`, with only `HOME` set. Expected: exit 0, and `nightly.log` holds `fake stockroom ingest` and `fake stockroom embed`.
  - Red today: `space` (exit 127) and `apostrophe` (`AssertionError` from `cron_install`). `plain` is green.
- **launchd.** Install through `launchd_install` with `FakeLaunchctl`. Load the plist, and run `ProgramArguments` with only `HOME` plus its `EnvironmentVariables`. Expected: exit 0, and the log holds both calls.
  - Red today: `space` and `apostrophe` (syntax errors). `plain` is green.
- **Unchanged and still green:** every existing schedule test. That includes the exact-payload test, because `tmp_path` holds only safe characters.

**Unit 2: contributor commands work from a checkout with a space or `'`** (new `test_contributor_paths.py`).

Checkout folders, parametrized: `plain`, `Jane Doe`, `O'Brien` (ids as above).

- **Make targets.** Copy the shipped `Makefile` alone into `<tmp>/<folder>/stockroom/`. Run `make --no-print-directory <target> UV=<fake uv>` there, with only `PATH` and `HOME` set. The fake uv lives in `<tmp>/fakebin`. It records `PYTHONPATH` and its arguments, and runs nothing. Parametrize over the targets and the number of uv calls each makes: `shim` 1, `torch` 2, `local-engine` 2 (the recursive `shim` call, then `ensure-env`), `local-dashboard` 1.
  - Expected: make exits 0, uv ran the expected number of times, every `--app-dir` value is `<checkout>/skills/sr-search`, and every `PYTHONPATH` that is set is `<checkout>/skills/sr-search/src`.
  - Red today: 8 cases (4 targets × `space` and `apostrophe`), as in the probe. That includes the silent `apostrophe`-`shim` case, which only the call count catches.
  - Skipped when `make` is not installed.
- **The localdev Claude hint.** Run the shipped `scripts/localdev.sh skills --harness claude --repo-root <checkout>`. Take the command between the backticks in its one line of output. Expected: `shlex.split` of it gives `["claude", "--plugin-dir", "<checkout>"]`.
  - Red today: `space` (four words) and `apostrophe` (`ValueError: No closing quotation`).

**Unit 3: Cursor's typed path survives a space and `'`** (`test_initialize_context.py`, a guard).

- A Cursor marketplace copy under a home whose path holds `O'Brien files`, rendered by `_fill_placeholder`, gives `("cursor", <copy>/skills/sr-search)`. It runs under every installed shell.
- Green today. It turns red if the placeholder line ever stops quoting the agent's path. That is the Cursor half of what round 3 covered for Claude Code, for the common characters.

**Mutation check** (a scratch script on a scratch copy, never in the worktree):

- M1: the log path is not quoted → all four non-plain cron and launchd cases go red.
- M2: the `PATH=` value is not quoted → the two non-plain cron cases go red.
- M3: `_sh_wrap` goes back to `'{payload}'` with its assert → the two non-plain cron cases go red. (The quoted log path now holds `'`.)
- M4: the Makefile's `shim` recipe has `--app-dir $(CURDIR)/$(ENGINE)` unquoted → the `shim` and `local-engine` cases go red for `space` and `apostrophe` (4).

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`.
- Conventions:
  - `test_schedule.py`: injected seams (`FakeCrontab`, `FakeLaunchctl`, a `which` function), a module docstring, and a docstring on every test.
  - `test_coverage_collection.py` is the precedent for subprocessing the root Make targets.
  - `test_initialize_context.py`: the `shell`, `step2` and `home` fixtures, `_fill_placeholder`, `_plugin_tree` and `_run_block`.
  - Subprocesses run with an explicit minimal environment.
- New test files: `skills/sr-search/tests/test_contributor_paths.py`. It gets a module docstring stating that the contributor commands must take the checkout path as one word.

## Implementation Plan

### 1. Nightly entries quote every path — executable

- Files: `skills/sr-search/tests/test_schedule.py`, `skills/sr-search/src/stockroom/schedule.py`

1. Stub tests: in `test_schedule.py`:
   - A helper, `_fake_shim_home(base: Path) -> tuple[Path, Which]`. It builds `base/stockroom-home/logs` and an executable fake `base/bin/stockroom`, and returns the home and a `which` that finds only the fake shim.
   - A helper, `_nightly_log_has_both_runs(home: Path) -> bool`.
   - Empty, documented tests, each parametrized over `plain`, `Jane Doe` and `O'Brien` with ids `plain`, `space`, `apostrophe`:
     - `test_cron_entry_runs_for_home_paths_with_spaces_and_quotes`
     - `test_launchd_entry_runs_for_home_paths_with_spaces_and_quotes`
   - Extend the module docstring: two tests run the rendered entries in a real `/bin/sh`, with a fake shim, never a real crontab or launchd.
2. Stub interface: none. The rendered entry is the interface, and no signature changes.
3. Write tests and run red:
   - Implement the helpers and both tests per the behaviors above.
   - Cron: `command = entry.split(" ", 5)[5]`, then `subprocess.run(["/bin/sh", "-c", command], env={"HOME": …}, cwd=base, capture_output=True, text=True)`.
   - launchd: `subprocess.run(data["ProgramArguments"], env={"HOME": …, **data["EnvironmentVariables"]}, …)`.
   - Run `uv run --no-sync --no-config pytest tests/test_schedule.py -n0` from `skills/sr-search` and read the whole output. Expected red set: 4 (space and apostrophe × cron and launchd). Every existing test and both `plain` cases stay green.
4. Write code and run green:
   - Add `import shlex`.
   - `render_payload` quotes the log path.
   - `_sh_wrap` returns `f"/bin/sh -c {shlex.quote(payload)}"` and drops the `'` assert.
   - `cron_install` writes `PATH={shlex.quote(path_prefix)}`.
   - Update the docstrings:
     - The module docstring: the entry quotes every path it carries.
     - `render_payload`: the log path is shell-quoted.
     - `_sh_wrap`: the payload is quoted as one word, and the `PATH=` reason stays.
   - Re-run until green. Then run the mutation check M1 to M3 (Unit 4 of Verification).

### 2. Contributor commands take the checkout path as one word — executable

- Files: `skills/sr-search/tests/test_contributor_paths.py` (new), `Makefile`, `scripts/localdev.sh`

1. Stub tests: create `test_contributor_paths.py` with:
   - A module docstring.
   - A fixture, `fake_uv(tmp_path) -> Path`, that writes `<tmp>/fakebin/uv`. The fake appends `PYTHONPATH=<value or <unset>>`, each argument on its own line, and `--end--` to `$FAKE_UV_LOG`.
   - A helper, `_uv_calls(log: Path) -> list[tuple[str, list[str]]]`.
   - Empty, documented tests:
     - `test_make_targets_take_the_checkout_path_as_one_word`, parametrized over the folder and over `(target, calls)` = `("shim", 1)`, `("torch", 2)`, `("local-engine", 2)`, `("local-dashboard", 1)`.
     - `test_localdev_claude_hint_is_a_runnable_command`, parametrized over the folder.
2. Stub interface: none.
3. Write tests and run red:
   - Make: copy `repo_root / "Makefile"` into `<tmp>/<folder>/stockroom/`. Run make with `cwd` there and `env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "FAKE_UV_LOG": …}`. Assert per the behaviors.
   - Hint: make `<tmp>/<folder>/stockroom`. Run `["sh", str(repo_root / "scripts" / "localdev.sh"), "skills", "--harness", "claude", "--repo-root", str(checkout)]`. Take the text between the backticks, and assert on its `shlex.split`.
   - Run red and read the whole output. Expected red set: 8 make cases and 2 hint cases. The 4 `plain` make cases and the `plain` hint stay green.
4. Write code and run green:
   - Makefile, four recipes: quote `"$(CURDIR)/$(ENGINE)/src"` and `--app-dir "$(CURDIR)/$(ENGINE)"`. Update the comment above `shim`: the paths are absolute and quoted, because a checkout path may hold spaces.
   - `localdev.sh` `skills_claude`: put `"${sc_root}"` in double quotes inside the hint.
   - Re-run until green, then run mutant M4.

### 3. Step 2: Cursor's typed path is pinned, and the error line is clearer — executable (guard test), then prose/policy (wording)

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests: add an empty, documented `test_cursor_placeholder_path_survives_a_quote_and_a_space(shell, step2, tmp_path)`.
2. Stub interface: none.
3. Write tests and run:
   - Implement the test. The home is `tmp_path / "O'Brien files" / "home"`, the copy is at `home/.cursor/plugins/cache/txrk9/stockroom/672cf3aa`, and the expected result is `("cursor", <copy>/skills/sr-search)`.
   - Run it. It passes today. It is a regression guard, not a red-first test: the behavior already holds, and the plan pins it. Record that in the build log as the expected result.
4. The error line is wording only. No tests: prose/policy artifact. A test of the message text could only go red when someone edits the text.
   - Replace the `else printf` line of the `*)` arm with the target line.
   - The existing tests already run both branches: `test_claude_custom_plugins_root_gets_no_owner` has no data folder, and `test_data_folder_in_another_plugins_root_proves_nothing` has one. So a broken line turns them red.
   - Re-run `test_initialize_context.py` in full and read the output.
   - Then render the shipped fence for those two cases under sh, bash and BusyBox sh with a scratch script, and read the stderr line each prints.

### 4. Step 2 prose, shared patterns, brief and repository memory — prose/policy

- Files: `skills/sr-initialize/SKILL.md`, `memory-bank/systemPatterns.md`, `memory-bank/active/projectbrief.md`, `.summem/notes/*` (written only through `.summem/summem note`)
- No tests: prose/policy artifact

1. `SKILL.md`, the Claude Code sub-bullet under the empty-`OWNER` bullet: replace "The block's error line shows the plugin data folder it was given." with "When Claude Code wrote a plugin data folder into the block, the error line names it and the folder it was expected in."
2. `systemPatterns.md`:
   - Under "Rendered-out artifacts: one tested owner each", add one sentence: every path a rendered artifact writes into shell text is quoted. The shim and the scheduler entries use `shlex.quote`, and the Makefile recipes put `$(CURDIR)` paths in double quotes.
   - The scheduler sentence in that section stays.
3. The brief:
   - Add "Added by rework round 4 (operator decision, 2026-10-18)" after AC10, with AC11. Paths that contain a space or `'` work everywhere stockroom writes them into shell text:
     - the Step 2 block, Steps 3 to 7, the shim and both hooks (already true);
     - the nightly cron and launchd entries;
     - the Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` targets;
     - `localdev.sh`'s printed hint.

     Other shell characters (`$`, a backtick, `"`, `\`, `%`) are out of scope.
   - AC10: "an error line that shows the data folder the block was given" becomes "an error line that names the data folder, when one was given".
4. One `.summem/summem note`, and follow any nap request the tool prints. Every path stockroom writes into shell text is quoted (heredoc, `shlex.quote`, double quotes), so a space or `'` works. Rare characters are out of scope.
5. Docs under `docs/`: no change. `docs/user-guide/load/schedule.md` names only the log location.

### 5. Verification

1. **Mutation check M1 to M4.** Write a scratch script, `mutation_check_r4.py`, modeled on `mutation_check_r3.py`. It runs each mutant on a scratch copy of the repo and runs `test_schedule.py` and `test_contributor_paths.py` there. Each mutant must turn red exactly its listed set, and the unmutated copy must pass.
2. **BusyBox.** Re-run preflight's `busybox_target_check.sh` from round 3 against the worktree's `SKILL.md`, and expect `PASS`: Step 2's head and rules are unchanged.
3. Run `make ci` from the repo root and read the whole output.
4. Run `claude plugin validate .` and confirm no new warnings.
5. The live shim is baked to `~/git/stockroom`, so the pre-commit `make format` sync of this worktree changes nothing outside it. Confirm with `grep '^# STOCKROOM_' ~/.local/bin/stockroom`.
6. **No live run of cron or launchd.**
   - Cron: this machine's real crontab is not touched. The test runs the entry the way cron(5) documents.
   - launchd: no macOS host is available. The test runs the plist's argument vector the way launchd.plist(5) documents.
   - The Step 2 live check from round 3 is not re-run. The heredoc and the substitution are unchanged, and only the stderr text changes.

## Technology Validation

No new technology - validation not required. `shlex` is in Python's standard library, and `stockroom.shim` already uses it. Double-quoting Make variables in recipes is plain shell. All three fixes were prototyped by the probes under Evidence.

## Dependencies

- cron passes an entry's command part to `/bin/sh -c` (crontab(5)); launchd runs `ProgramArguments` without a shell (launchd.plist(5)).
- `/bin/sh` and `make` exist on the test hosts. `make` is already required by `test_coverage_collection.py`, and the Make cases skip without it.
- Round 3's Step 2 head and owner rules, unchanged.

## Challenges & Mitigations

- **Users whose space-holding home already has a broken entry keep it.** Step 8 skips scheduling when `status` says installed, and `status` cannot tell a broken entry from a good one. Mitigation: the PR #142 text tells them to re-run `stockroom schedule install`, which replaces the entry. A self-healing check is out of scope.
- **The quoted entry is hard to read for odd homes.** For a home with a space, `stockroom schedule status` shows `'"'"'`-style quoting. Plain homes look exactly as before. Accepted: the entry is correct, and Step 8 only checks its fire time.
- **The exact-payload test depends on `tmp_path`.** It holds only characters `shlex.quote` leaves alone (pytest names folders from test names). If that ever changes, the test fails loudly, not silently.
- **The fake uv must not sit under the odd folder.** `$(UV)` stays unquoted (out of scope). The tests keep the fake under `<tmp>/fakebin`.
- **Recursive make.** `local-engine` calls `$(MAKE) shim`. A command-line `UV=` passes down through `MAKEFLAGS`, which the probe confirms with 2 calls.
- **The `'` `shim` case passes on exit status alone.** Only the uv call count catches it, so the call count is part of every Make assertion.
- **zsh is still never run**, here or in CI (carried).

## Pre-Mortem

- **The inventory missed a place.** The table names the search used, and preflight and QA re-run it. Anything new found there goes into this round, not a follow-up.
- **The tests model cron and launchd, and the real ones behave differently.** Both models follow the documented contract: cron passes the command part to `/bin/sh -c`, and launchd runs an argument vector. Cron's own `%` and environment rules are unchanged by this round. A real launchd run is not possible here, so QA should read the plist the test writes.
- **Scope creep into contributor tooling.** The Makefile and the hint are contributor-facing. They are in scope because Step 7 of `sr-initialize` sends contributors to `make shim`, which is the same command class, and because the operator's rule is common and breaking. Each fix is a one-word quoting change. If the operator strikes them, Unit 2 drops out whole.
- **The error line adds an expansion that one shell parses differently.** The probe ran it under dash, bash and BusyBox sh. Verification step 2 re-runs the BusyBox check on the shipped block.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
