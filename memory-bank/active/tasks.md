# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

**Rework round 4: paths with a space or `'` work wherever stockroom writes them into shell text, and the nightly job runs against the warehouse it was installed for.**

- Rounds 1 to 3 are complete through Reflect on this branch. Round 3's plan, with its build and QA records, is in git at 0e458e9 (`memory-bank/active/tasks.md`).
- The first round 4 plan (c0fc32f) failed preflight, fixable. This is the revised plan. The dispositions are at the end.
- The history of all rounds is in `progress.md`.

Round 3 read Claude Code's pasted paths from a quoted heredoc, which fixed one place a path meets a shell. The operator then asked for every such place. This round inventories them all and fixes each one where a common character, a space or `'`, breaks it. The breaking places:

- **The nightly job.**
  - Under cron, a stockroom home or shim folder with a space fails every night with exit 127 and writes no log. A `'` makes `stockroom schedule install` raise `AssertionError`. Under launchd, both characters give a shell syntax error every night. Nobody is watching when this happens.
  - **Found by preflight:** cron and launchd pass on neither `STOCKROOM_HOME` nor `XDG_DATA_HOME`, so the nightly job always uses the default warehouse at `~/.local/share/stockroom`. For a user with a custom home, it quietly builds a second warehouse while the real one goes stale, and the log in the real home reports success.
    - This has been true for every custom-home user since scheduling shipped, with plain paths too.
    - A space in the path almost always comes from a custom home, so fixing the quoting alone would turn a failing job into one that writes to the wrong warehouse.
  - Entries already installed are never re-rendered: Step 8 skips scheduling when `status` says installed.
- **The Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` recipes.**
  - A checkout path with a space fails.
  - With a `'`, plain `make shim` exits 0 and runs nothing: the two `'` on that recipe line pair up, and the whole command becomes one variable assignment.
  - Step 7 of `sr-initialize` sends contributors to `make shim`.
- **`localdev.sh`'s Claude hint.** It prints `claude --plugin-dir <checkout>` unquoted, so the command a contributor copies splits at the space.
- **QA follow-up 1 from round 3.** This one is wording, not quoting. Step 2's error line says "the plugin data folder (not given)" when nothing was substituted. In Cursor, that names a Claude Code idea, and so does "no install record lists it".

Who it helps:

- Users with a custom stockroom home (`STOCKROOM_HOME` or `XDG_DATA_HOME`). Their nightly job starts using their own warehouse. With a space or `'` in the path, such as `~/Library/Application Support` on macOS or `/mnt/c/Users/Jane Doe` under WSL, it also starts running at all.
- Users with a space or `'` in `HOME` or `~/.local/bin`.
- Users who already have one of these entries. The next `sr-initialize` run reports the entry as out of date and offers to re-install it.
- Contributors whose checkout path holds a space or `'`.

Cursor users get no new questions about their harness. Their Step 2 path already works with both characters, and this round adds a test that keeps it that way. The one new question, whether to re-install an out-of-date nightly entry, is the same in every harness.

### Operator decisions (2026-10-18)

- **Fix what is both common and breaking.** The operator: "Let's fix things that are both common and breaking. so, "space in path," yeah. "if someone puts cryllic diacritics in-between 4 special shell characters in their homedir," no."
  - In scope: a space or `'` in any path stockroom writes into shell text.
  - Out of scope: `$`, a backtick, `"`, `\` and `%` in folder names. Where those still break, the inventories list them instead of fixing them.
- **Fix every instance, not one.** The operator objected that round 3 "just fixed 1 frickin place". So the inventories below cover every place stockroom writes a path into shell text, and every variable the nightly job needs. Each gets a result.
- Earlier decisions stand (round 3's plan, at 0e458e9):
  - the failure principles (brief AC10);
  - contributors always get `dev`;
  - hooks stay as they are;
  - no Claude-driven questions for Cursor users.

### Inventory 1: every place stockroom writes a path into shell text

How it was built:

- A search of all tracked code, scripts, hooks and skill files outside `docs/` and the tests, for shell runs (`shell=True`, `os.system`, `sh -c`, `subprocess`, `shlex`).
- A read of every bash fence in every `SKILL.md` and skill reference.
- A read of the Makefile, `scripts/localdev.sh`, both hook files and the shim template.
- Probes with spaces and `'` (Evidence). Preflight re-ran the search and found nothing new.

| Where | Who writes the path | Space | `'` | This round |
| --- | --- | --- | --- | --- |
| Step 2, Claude Code's pasted paths (quoted heredoc) | Claude Code | works | works | none (round 3) |
| Step 2, Cursor's placeholder `SKILL_DIR="<…>"` | the agent | works (inside `"…"`) | works | guard test (Unit 4) |
| Step 2's printed line `APP_DIR='…'` | the block | works | works (AC8) | none |
| Steps 3 to 7: `"$APP_DIR"`, `--app-dir "$APP_DIR"` | the printed line | works | works | none |
| Step 7, `ls -dL -- "<STOCKROOM_APP_DIR>/pyproject.toml"` | the agent, from the shim header | works (inside `"…"`) | works | none |
| Step 7, `grep … ~/.local/bin/stockroom` | the shell (`~`) | works (tilde results are not split) | works | none |
| The shim (`APP_DIR=` via `shlex.quote`, then `"$APP_DIR"`) | the engine | works | works | none |
| The Claude Code hook (`"${CLAUDE_PLUGIN_ROOT}"`, expanded from the environment) | Claude Code | works | works | none |
| The Cursor hooks (`"${CURSOR_PLUGIN_ROOT}"`, double-quoted either way) | Cursor | works | works | none |
| The cron entry: the log path and the `PATH=` value | the engine | **breaks**: exit 127 every night, no log | **breaks**: `schedule install` raises `AssertionError` | Unit 1 |
| The launchd payload: the log path | the engine | **breaks**: syntax error every night | **breaks**: syntax error every night | Unit 1 |
| Makefile `shim`, `torch`, `local-engine`, `local-dashboard` | `$(CURDIR)` | **breaks**: exit 2 or 127 | **breaks**: syntax error, or `make shim` exits 0 having run nothing | Unit 3 |
| `localdev.sh`'s printed `claude --plugin-dir …` hint | the script | **breaks** when copied | **breaks** when copied | Unit 3 |
| `localdev.sh`, every other path | the script | works (all quoted) | works | none |
| Makefile, every other recipe | `$(CURDIR)` quoted, or relative paths | works | works | none |
| Other skills' fences (`sr-query`, `sr-semantic`, `sr-dashboard`, cookbook) | none | no paths | no paths | none |
| Engine subprocess calls (`doctor`, `engine_env`, `torch_source`, `dashboard`, `shim`) | the engine | argv lists, no shell | same | none |
| launchd's `EnvironmentVariables`, `StandardOutPath` and `StandardErrorPath` | the engine | plist values, no shell | same | none |

Out of scope, and still breaking for the rare characters (operator decision):

- The Step 2 placeholder and the Step 7 typed path, for `$`, a backtick, `"` or `\`.
- The Cursor hooks for the same characters, if Cursor pastes its root in as text. Whether it does is unverified.
- `%` anywhere in a cron entry (cron reads `%` as a newline).
- `$(UV)` and `$(LOCALDEV_SH)` in the Makefile. These are tool and script paths, not the checkout path.
- The docs' example commands, which are placeholders for a person to fill in.

The scheduler fix also handles `$`, a backtick and `"`, because `shlex.quote` covers every character. The first probe shows that for `$x`.

### Inventory 2: what the nightly job needs from the user's environment

cron and launchd load no shell profile. cron gives a job `HOME`, `LOGNAME`, `SHELL` and `PATH=/usr/bin:/bin`. launchd gives what the plist sets. Each variable the engine reads (a search for `os.environ` in `src/stockroom`):

| Variable | What it changes | The nightly job today | This round |
| --- | --- | --- | --- |
| `PATH` | finding the shim and `uv` | carried, resolved at install | quoted (Unit 1) |
| `STOCKROOM_HOME`, `XDG_DATA_HOME` | which warehouse, plus the log, the torch freeze | **dropped**: the job uses `~/.local/share/stockroom` | **carried** as the resolved home, `STOCKROOM_HOME=<home>` (Unit 1) |
| `HOME` | the defaults above | set by cron and launchd | none |
| `XDG_CONFIG_HOME` | where optional `config.toml` pins live (extra Cursor enrichment DBs; `state_vscdb` is backfill only) | dropped | none: a non-default config home is rare, and the pins are additive, so the job loses extra enrichment, not data |
| `STOCKROOM_CURSOR_ROOT`, `STOCKROOM_CURSOR_CHATS_ROOT`, `STOCKROOM_CLAUDE_ROOT` | ingest source folders | dropped | none: the docs present them as one-shot prefixes (`STOCKROOM_CLAUDE_ROOT=… stockroom ingest`) |
| `STOCKROOM_AI_TRACKING_DB` | forces one enrichment DB | dropped | none: documented "for tests or one-shots" |
| `STOCKROOM_CURSOR_STATE_VSCDB` | the backfill source | not used | none: backfill is never scheduled |

Where this search stops: it covers only the variables stockroom's own code reads. cron and launchd also drop the variables libraries read. For example, with a custom `HF_HOME`, the nightly embed downloads the embedding model again, once, into the default cache. That does not break the job, so it is out of scope (preflight 2, advisory 7).

The home is carried always, not only when it is custom. The entry then states which warehouse it serves, and it agrees with its own log path by construction. A user who later moves their home re-installs, which is the same as today for the log path, and Unit 2's `status` reports that case as out of date.

### Evidence that shaped the plan

- **Scheduler quoting, today vs planned** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/schedule_fix_probe.py`).
  - Setup: the stockroom home and a fake `stockroom` shim both sit under a folder named `plain`, `Jane Doe`, `O'Brien` or `cost$x`.
  - It runs the cron command part as cron does (`<shell> -c <command>`) and the launchd `ProgramArguments` as launchd does, under dash, bash and BusyBox sh.
  - Today: 18 of the 18 non-plain cases fail.
    - Space: cron exits 127 ("Doe/bin:/usr/bin:/bin: not found"), and launchd exits 2.
    - `'`: cron rendering raises `AssertionError`, and launchd exits 2.
    - `$x`: the log cannot be created.
  - Planned (`shlex.quote` on the log path, the `PATH=` value and the whole payload): all 24 cases pass.
- **The nightly job's home** (preflight's `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/preflight-r4/scripts/custom_home_probe.py`).
  - Setup: `STOCKROOM_HOME`, and separately `XDG_DATA_HOME`, set to `<home>/Library/Application Support`, with the first plan's rendering.
  - Result: both entries exit 0 and log into the custom home. But the engine's own `resolve_home()`, run under the scheduler's environment, answers `<home>/.local/share/stockroom` (source `default`).
- **The planned home carry** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/schedule_home_probe.py`).
  - Renderings: cron as `PATH=<q> STOCKROOM_HOME=<q> /bin/sh -c <q payload>`; launchd with `STOCKROOM_HOME` in `EnvironmentVariables`.
  - For `plain`, `Jane Doe` and `O'Brien`, under cron with sh, bash and BusyBox sh, and once for launchd: 12 of 12 pass. The fake shim saw the install home on both calls.
- **Makefile, today vs planned** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/make_quoting_probe.sh`).
  - Setup: the Makefile alone is copied into `<tmp>/<name>/stockroom/`, and each target runs with a fake `uv`.
  - Today: plain passes, and 8 of 8 space and `'` cases fail.
    - With `'`, plain `make shim` exits 0 with no `uv` call.
    - `make shim TAKEOVER=1` and `local-engine` exit 127 instead (preflight advisory 6).
  - Planned: 12 of 12 pass.
- **The Step 2 error line** (`/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/error_line_probe.sh`, and preflight's `error_line_render.sh` on the whole fence).
  - dash, bash and BusyBox sh print the same text in both branches.
  - zsh is not installed here (carried).
- **Documented behavior the tests model:**
  - cron runs "the entire command portion of the line, up to a newline or % character" with `/bin/sh`, in a minimal environment ([crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html)).
  - launchd runs `ProgramArguments` as an argument vector, without a shell, with the plist's `EnvironmentVariables` ([launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html)).
  - `shlex.quote` returns "a shell-escaped version of the string", safe as one token for a POSIX shell, and leaves strings of safe characters unchanged ([Python docs](https://docs.python.org/3/library/shlex.html#shlex.quote)).

### Target design

**`stockroom.schedule`** (`import shlex`):

```python
def render_payload(home: Path) -> str:
    payload = f"(date; stockroom ingest && stockroom embed) >> {shlex.quote(str(_log_path(home)))} 2>&1"

def _sh_wrap(payload: str) -> str:
    return f"/bin/sh -c {shlex.quote(payload)}"

def _cron_entry(hour: int, minute: int, home: Path, path_prefix: str) -> str:
    """The one managed crontab line: time fields, PATH, the home, the wrapped payload."""
    return (
        f"{minute} {hour} * * * PATH={shlex.quote(path_prefix)} "
        f"{warehouse.HOME_ENV_VAR}={shlex.quote(str(home))} {_sh_wrap(render_payload(home))}"
    )

def _launchd_job(hour: int, minute: int, home: Path, path_prefix: str) -> dict:
    """The owned plist's content."""
    log = str(_log_path(home))
    return {
        "Label": PLIST_LABEL,
        "ProgramArguments": ["/bin/sh", "-c", render_payload(home)],
        "EnvironmentVariables": {"PATH": path_prefix, warehouse.HOME_ENV_VAR: str(home)},
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }
```

Notes on the scheduler design:

- `warehouse.HOME_ENV_VAR` is `stockroom.home`'s constant, which `warehouse` (already imported by `schedule`) re-exports.
- `cron_install` and `launchd_install` write what these helpers return.
- `shlex.quote` leaves a path of safe characters unchanged, so a plain home's payload is byte for byte what it is today. The entry gains one assignment, `STOCKROOM_HOME=<home>`. The existing tests use substring checks on the entry, and preflight ran them green on the first design.
- The `'` assert in `_sh_wrap` goes, because `shlex.quote` handles `'`. The `%` assert in `render_payload` stays, since `%` is out of scope.

**`schedule status`** gains one fact when an entry is installed: `up-to-date: yes`, `no` or `unknown`.

- `cron_status` reads the managed line's minute and hour, and compares the line with `_cron_entry(hour, minute, home, _path_prefix(which))`.
- `launchd_status` compares the plist with `_launchd_job(…)` for its own interval.
- The result is `unknown` when the shim is not on `PATH`, because then nothing can be rendered. It is `no` when the managed line's time fields do not parse.
- Both functions take an injectable `which` (default `shutil.which`), like the install functions.
- When an entry is installed, `status` also prints `entry home: <path>`: the `STOCKROOM_HOME` the installed job carries (preflight 2, advisory 2).
  - It prints `entry home: not set` for an entry that carries none, such as every 2.1.1 entry. Such a job uses `~/.local/share/stockroom`.
  - It prints `entry home: unreadable` for a cron line that `shlex.split` cannot parse.
  - Cron reads the value from the line's `STOCKROOM_HOME=` word, and launchd from `EnvironmentVariables`.
  - With this line beside `log:`, which shows the home `status` itself used, the agent can tell the user whether a re-install would move the job to another warehouse. On launchd nothing else shows it.

**Step 8 of `sr-initialize`:**

- **`up-to-date: no`:** the entry was written by an older stockroom, or for another stockroom home or `PATH`. Tell the user, and offer to re-install it at the time it already has. Re-install only with their consent.
- **`up-to-date: unknown`:** go back to Step 7.

**Makefile:** in the `torch`, `shim`, `local-engine` and `local-dashboard` recipes, use `PYTHONPATH="$(CURDIR)/$(ENGINE)/src"` and `--app-dir "$(CURDIR)/$(ENGINE)"`.

**`localdev.sh`:** ``use `claude --plugin-dir \"${sc_root}\"` for a session-scoped plugin load``.

**Step 2's error line** (replaces the `else printf` line of the `*)` arm; preflight advisory 2):

```bash
      else printf 'sr-initialize: %s is laid out like an installed plugin outside the default plugins folders, and nothing proves who installed it%s\n' "$APP_DIR" "${PLUGIN_DATA:+; its plugin data folder $PLUGIN_DATA is not in ${CACHE_DIR%/*}/data}" >&2
```

- It uses the words of the skill's own empty-`OWNER` bullet, which hold in every harness.
- With a data folder, it names the folder and where it was expected.

## Test Plan (TDD)

### Behaviors to Verify

**Unit 1: the nightly entries run, for the install home, with a space or `'` in the path** (`test_schedule.py`).

Setup for each case:

- It builds `<tmp>/<folder>/stockroom-home` and an executable fake `<tmp>/<folder>/bin/stockroom`. The fake prints `fake stockroom <args> home=${STOCKROOM_HOME-<unset>}`.
- So the log path, the `PATH=` value and the carried home all hold the folder name.
- Folders, parametrized: `plain`, `Jane Doe`, `O'Brien` (ids `plain`, `space`, `apostrophe`).

The cases:

- **Cron.** Install through `cron_install` with `FakeCrontab` and a `which` that finds only the fake shim. Take the entry's command part (after the five time fields), and run it as cron does: `/bin/sh -c <command part>`, with only `HOME` set.
  - Expected: exit 0, and `nightly.log` holds the lines `fake stockroom ingest home=<home>` and `fake stockroom embed home=<home>`.
  - Red today, all three: `plain` sees `home=<unset>`; `space` exits 127; `apostrophe` raises `AssertionError`.
- **launchd.** Install through `launchd_install` with `FakeLaunchctl`. Load the plist, and run `ProgramArguments` with only `HOME` plus its `EnvironmentVariables`.
  - Expected: the same.
  - Red today, all three: `plain` sees `<unset>`, and `space` and `apostrophe` hit syntax errors.
- **Unchanged and still green:** every existing schedule test, including the exact-payload test (`tmp_path` holds only safe characters) and the plist-shape test (it reads `PATH` by key).

**Unit 2: `schedule status` says whether the installed entry is up to date** (`test_schedule.py`).

- **Cron, fresh.** `cron_install`, then `cron_status` with the same runner, `which` and home → the lines include `up-to-date: yes` and `entry home: <home>`.
- **Cron, older.** A crontab whose managed block holds the 2.1.1 rendering for the same home and fake `which` (no `STOCKROOM_HOME`, single-quoted payload, written out in the test) → `up-to-date: no` and `entry home: not set`.
- **launchd, fresh.** `launchd_install`, then `launchd_status` with the same `which` → `up-to-date: yes` and `entry home: <home>`.
- **launchd, older.** A plist in the 2.1.1 shape (`EnvironmentVariables` holds only `PATH`) → `up-to-date: no` and `entry home: not set`.
- **Existing status tests** pass `which=fake_which`, so they no longer read the real `PATH` (preflight 2, minor note). Their assertions are unchanged.
- **No shim on PATH.** For both schedulers (parametrized `cron` and `launchd`), an installed entry with `which_without_shim` → `up-to-date: unknown`.
- Red today: all 6, because there is no such fact.
- **Unchanged:** not installed → no `up-to-date:` line. The existing status tests keep passing.

**Unit 3: contributor commands take the checkout path as one word** (new `test_contributor_paths.py`).

Checkout folders, parametrized: `plain`, `Jane Doe`, `O'Brien`, with ids as above.

- **Make targets.**
  - Setup: copy the shipped `Makefile` alone into `<tmp>/<folder>/stockroom/`. Run `make --no-print-directory <target> UV=<stub_uv bin>/uv` there, with only `PATH` and `HOME` set.
  - The fake is `conftest.py`'s `stub_uv`, reused (preflight advisory 3). It prints `UV_PYTHONPATH:` and `UV_ARG:` lines, and its bin dir `tmp_path/stub-bin` sits outside the odd folder.
  - Parametrize over the targets and the number of uv calls each makes: `shim` 1, `torch` 2, `local-engine` 2 (the recursive `shim` call, then `ensure-env`), `local-dashboard` 1.
  - Expected:
    - make exits 0;
    - stdout holds the expected number of `UV_PYTHONPATH:` lines;
    - every `UV_ARG:` after `UV_ARG:--app-dir` is `<checkout>/skills/sr-search`;
    - every non-empty `UV_PYTHONPATH:` value is `<checkout>/skills/sr-search/src`.
  - Red today: 8 (4 targets × `space` and `apostrophe`). That includes the silent `apostrophe`-`shim` case, which only the call count catches.
  - Skipped when `make` is not installed.
- **The localdev Claude hint.** Run the shipped `scripts/localdev.sh skills --harness claude --repo-root <checkout>`, and take the command between the backticks in its one line of output.
  - Expected: `shlex.split` gives `["claude", "--plugin-dir", "<checkout>"]`.
  - Red today: `space` (four words) and `apostrophe` (`ValueError: No closing quotation`).

**Unit 4: Cursor's typed path survives a space and `'`** (`test_initialize_context.py`, a guard).

- A Cursor marketplace copy under a home whose path holds `O'Brien files` is rendered by `_fill_placeholder`. Expected: `("cursor", <copy>/skills/sr-search)`, under every installed shell.
- Green today. It turns red if the placeholder line ever stops quoting the agent's path. That is the Cursor half of what round 3 covered for Claude Code, for the common characters.

**Mutation check.** Build extends preflight's `run_r4_variants.py` (preflight advisory 5). It runs on scratch copies, never in the worktree.

| Mutant | Change | Predicted red set |
| --- | --- | --- |
| M1 | the log path is not quoted | 4: space and apostrophe, for cron and launchd |
| M2 | the cron `PATH=` value is not quoted | 2: cron space and apostrophe |
| M3 | the cron `STOCKROOM_HOME=` value is not quoted | 2: cron space and apostrophe |
| M4 | `_sh_wrap` goes back to `'{payload}'` with its assert | 2: cron space and apostrophe (the quoted log path now holds `'`) |
| M5 | no `STOCKROOM_HOME` in the cron entry | 4: all 3 cron entry cases, plus the cron "older" status test. The mutant then renders the 2.1.1 entry byte for byte (preflight 2, advisory 1). The cron "fresh" test stays green, because status renders the same way. |
| M6 | no `STOCKROOM_HOME` in the plist | 4: all 3 launchd entry cases, plus the launchd "older" status test (same reason) |
| M7 | status says `up-to-date: yes` for any installed entry | 4: both "older" cases and both "no shim" cases |
| M8 | the Makefile's `shim` recipe has `--app-dir $(CURDIR)/$(ENGINE)` unquoted | 4: `shim` and `local-engine`, for space and apostrophe |

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`.
- Conventions:
  - `test_schedule.py`: injected seams (`FakeCrontab`, `FakeLaunchctl`, `which` functions), a module docstring, and a docstring on every test.
  - `conftest.py` provides the `stub_uv` and `repo_root` fixtures.
  - `test_coverage_collection.py` is the precedent for subprocessing the root Make targets.
  - `test_initialize_context.py`: the `shell`, `step2` and `home` fixtures, `_fill_placeholder`, `_plugin_tree` and `_run_block`.
  - Subprocesses run with an explicit minimal environment.
- New test files: `skills/sr-search/tests/test_contributor_paths.py`. It gets a module docstring: the contributor commands must take the checkout path as one word.

## Implementation Plan

### 1. Nightly entries quote every path and carry the stockroom home — executable

- Files: `skills/sr-search/tests/test_schedule.py`, `skills/sr-search/src/stockroom/schedule.py`

1. Stub tests: in `test_schedule.py`:
   - A helper, `_fake_shim_home(base: Path) -> tuple[Path, Which]`. It builds `base/stockroom-home/logs` and the executable fake `base/bin/stockroom`, and returns the home and a `which` that finds only the fake shim.
   - A helper, `_nightly_runs(home: Path) -> list[str]`, which returns the log's `fake stockroom …` lines.
   - Two empty, documented tests, each parametrized over `plain`, `Jane Doe` and `O'Brien` with ids `plain`, `space` and `apostrophe`:
     - `test_cron_entry_runs_for_the_install_home`
     - `test_launchd_job_runs_for_the_install_home`
   - Extend the module docstring: these tests run the rendered entries in a real `/bin/sh`, with a fake shim, never a real crontab or launchd.
2. Stub interface: none. The rendered entry is the interface, and Unit 2 adds the helpers.
3. Write tests and run red:
   - Implement the helpers and both tests per the behaviors above.
   - Cron: `command = entry.split(" ", 5)[5]`, then `subprocess.run(["/bin/sh", "-c", command], env={"HOME": str(base)}, cwd=base, capture_output=True, text=True)`.
   - launchd: `subprocess.run(data["ProgramArguments"], env={"HOME": str(base), **data["EnvironmentVariables"]}, …)`.
   - Run `uv run --no-sync --no-config pytest tests/test_schedule.py -n0` from `skills/sr-search` and read the whole output. Expected red set: 6 (3 folders × cron and launchd). Every existing test stays green.
4. Write code and run green:
   - Add `import shlex`. Name the variable through `warehouse.HOME_ENV_VAR`.
   - `render_payload` quotes the log path.
   - `_sh_wrap` returns `f"/bin/sh -c {shlex.quote(payload)}"` and drops the `'` assert.
   - `cron_install` writes `PATH={shlex.quote(path_prefix)} STOCKROOM_HOME={shlex.quote(str(home))} …`.
   - `launchd_install` adds `STOCKROOM_HOME` to `EnvironmentVariables`.
   - Update the docstrings:
     - The module docstring: the entry carries `PATH` and the resolved home, because neither scheduler loads a profile, and it quotes every path.
     - `render_payload`: the log path is shell-quoted.
     - `_sh_wrap`: the payload is one quoted word, and the reason for the `PATH=` prefix stays.
   - Re-run until green.

### 2. `schedule status` says whether the installed entry is up to date — executable

- Files: `skills/sr-search/tests/test_schedule.py`, `skills/sr-search/src/stockroom/schedule.py`

1. Stub tests:
   - Six empty, documented tests:
     - `test_cron_status_says_a_fresh_entry_is_up_to_date`
     - `test_cron_status_says_an_older_entry_is_not_up_to_date`
     - `test_launchd_status_says_a_fresh_job_is_up_to_date`
     - `test_launchd_status_says_an_older_job_is_not_up_to_date`
     - `test_status_cannot_judge_an_entry_without_the_shim`, parametrized over `cron` and `launchd`
   - Extend the module docstring's coverage list: the up-to-date fact.
2. Stub interface:
   - Move the rendering out of the install functions into `_cron_entry(hour, minute, home, path_prefix) -> str` and `_launchd_job(hour, minute, home, path_prefix) -> dict`, with docstrings, and have both install functions call them. This is a behavior-preserving refactor: Unit 1's tests stay green.
   - `cron_status` and `launchd_status` gain `which: Which = shutil.which`, documented, and still unused.
3. Write tests and run red:
   - Implement the six tests per the behaviors above. The "older" cases write the 2.1.1 rendering out in the test: for cron, the managed block line; for launchd, the plist dict with only `PATH`. Both use the same home and `fake_which`.
   - Run red and read the whole output. Expected red set: 6. Every Unit 1 test and every existing test stay green.
4. Write code and run green:
   - `cron_status`, when an entry is installed:
     - parse its first two fields as minute and hour;
     - compare the line with `_cron_entry(…)` for `_path_prefix(which)`;
     - append `up-to-date: yes|no|unknown`.
   - `launchd_status` does the same against `_launchd_job(…)` for the plist's interval.
   - Both append `entry home: <path>|not set|unreadable`, as in the target design.
   - Update both docstrings and the `status` help text in `_build_parser`.
   - Re-run until green.

### 3. Contributor commands take the checkout path as one word — executable

- Files: `skills/sr-search/tests/test_contributor_paths.py` (new), `Makefile`, `scripts/localdev.sh`

1. Stub tests: create `test_contributor_paths.py` with:
   - a module docstring;
   - a helper, `_uv_calls(stdout: str) -> list[tuple[str, list[str]]]`, which parses `stub_uv`'s labelled lines into (`PYTHONPATH`, args) per call;
   - two empty, documented tests:
     - `test_make_targets_take_the_checkout_path_as_one_word`, parametrized over the folder and over `(target, calls)` = `("shim", 1)`, `("torch", 2)`, `("local-engine", 2)`, `("local-dashboard", 1)`;
     - `test_localdev_claude_hint_is_a_runnable_command`, parametrized over the folder.
2. Stub interface: none.
3. Write tests and run red:
   - Make:
     - Copy `repo_root / "Makefile"` into `<tmp>/<folder>/stockroom/`.
     - Run make with `cwd` there, `UV=str(stub_uv / "uv")`, and `env={"PATH": f"{stub_uv}{os.pathsep}{os.environ['PATH']}", "HOME": str(tmp_path)}`. With `stub_uv` first on `PATH`, a recipe that ever skipped `$(UV)` still could not reach the real `uv` and replace the live dashboard (preflight 2, advisory 6).
     - Assert per the behaviors.
   - Hint:
     - Make `<tmp>/<folder>/stockroom`.
     - Run `["sh", str(repo_root / "scripts" / "localdev.sh"), "skills", "--harness", "claude", "--repo-root", str(checkout)]`.
     - Take the text between the backticks, and assert on its `shlex.split`.
   - Run red and read the whole output. Expected red set: 8 make cases and 2 hint cases. The 4 `plain` make cases and the `plain` hint stay green.
4. Write code and run green:
   - Makefile: in the four recipes, quote `"$(CURDIR)/$(ENGINE)/src"` and `--app-dir "$(CURDIR)/$(ENGINE)"`. Update the comment above `shim`: the paths are absolute and quoted, because a checkout path may hold a space.
   - `localdev.sh` `skills_claude`: put `"${sc_root}"` in double quotes inside the hint.
   - Re-run until green.

### 4. Step 2: Cursor's typed path is pinned, and the error line is clearer — executable (guard test), then prose/policy (wording)

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests: add an empty, documented `test_cursor_placeholder_path_survives_a_quote_and_a_space(shell, step2, tmp_path)`.
2. Stub interface: none.
3. Write tests and run:
   - Implement the test:
     - the home is `tmp_path / "O'Brien files" / "home"`;
     - the copy is at `home/.cursor/plugins/cache/txrk9/stockroom/672cf3aa`;
     - the expected result is `("cursor", <copy>/skills/sr-search)`.
   - Run it. It passes today. It is a regression guard, not a red-first test: the behavior already holds, and the plan pins it. Record that in the build log as the expected result.
4. The error line is wording only. No tests: prose/policy artifact. A test of the message text could only go red when someone edits the text.
   - Replace the `else printf` line of the `*)` arm with the target line.
   - The existing tests already run both branches: `test_claude_custom_plugins_root_gets_no_owner` has no data folder, and `test_data_folder_in_another_plugins_root_proves_nothing` has one. So a broken line turns them red.
   - Re-run `test_initialize_context.py` in full and read the output.
   - Re-run preflight's `error_line_render.sh` on the shipped fence under sh, bash and BusyBox sh, and read the stderr line each prints.

### 5. Prose: Step 2 and Step 8, the scheduling doc, shared patterns, brief and repository memory — prose/policy

- Files:
  - `skills/sr-initialize/SKILL.md`
  - `docs/user-guide/load/schedule.md`, `docs/user-guide/troubleshooting/index.md`
  - `memory-bank/systemPatterns.md`
  - `memory-bank/active/projectbrief.md`
  - `.summem/notes/*` (written only through `.summem/summem note`)
- No tests: prose/policy artifact

1. `SKILL.md`:
   - Step 2, the Claude Code sub-bullet under the empty-`OWNER` bullet: replace "The block's error line shows the plugin data folder it was given." with "When Claude Code wrote a plugin data folder into the block, the error line names it and the folder it was expected in."
   - The opening "Idempotent by design" paragraph: "`stockroom schedule status` says installed → skip scheduling" becomes "says installed and up to date → skip scheduling" (preflight 2, advisory 3).
   - Step 8, the `status` paragraph: add the `up-to-date:` and `entry home:` facts.
     - `yes`: the step is done.
     - `no`: the entry was written by an older stockroom, or for another stockroom home or `PATH`.
       - Tell the user what differs. Compare `entry home:` (the home the job uses now; `not set` means `~/.local/share/stockroom`) with `log:` (the home a re-install would use).
       - Offer to re-install it at the time it already has, with `stockroom schedule install --time HH:MM`. Re-install only with their consent.
     - `unknown`: the `stockroom` command is not on PATH; go back to Step 7.
2. `docs/user-guide/load/schedule.md`, after the `install` paragraph:
   - The entry carries the stockroom home it was installed for, because cron and launchd do not load your shell profile.
   - If you change `STOCKROOM_HOME` or `XDG_DATA_HOME`, or `status` says `up-to-date: no`, run `stockroom schedule install --time HH:MM` again with your time. Without `--time`, install uses 03:30 (preflight 2, advisory 4).
   - `docs/user-guide/troubleshooting/index.md`, "Nightly schedule installed but nothing updates": also check `up-to-date:` and `entry home:` in `status`, and re-install when it says `no` (preflight 2, advisory 5).
3. `systemPatterns.md` (preflight advisory 4):
   - A short cross-cutting paragraph, "Paths in shell text": wherever stockroom writes a path into shell text, it is quoted.
     - Step 2 reads pasted paths from a quoted heredoc and prints a `'`-escaped line.
     - The shim and the scheduler entries use `shlex.quote`.
     - The Makefile recipes double-quote `$(CURDIR)` paths.
     - A space and `'` must work; rarer shell characters are out of scope.
   - In "Rendered-out artifacts", extend the scheduler sentence:
     - entries carry `PATH` and the resolved `STOCKROOM_HOME`, because neither scheduler loads a profile;
     - `schedule status` reports whether the installed entry matches the current rendering.
4. The brief:
   - Add "Added by rework round 4 (operator decision, 2026-10-18)" after AC10, with two criteria:
     - **AC11.** Paths that contain a space or `'` work everywhere stockroom writes them into shell text:
       - the Step 2 block, Steps 3 to 7, the shim and both hooks (already true);
       - the nightly cron and launchd entries;
       - the Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` targets;
       - `localdev.sh`'s printed hint.

       Other shell characters (`$`, a backtick, `"`, `\`, `%`) are out of scope.
     - **AC12.** The nightly job runs against the stockroom home it was installed for. `schedule status` reports an installed entry that differs from the current rendering, and `sr-initialize` then offers to re-install it.
   - AC10: "an error line that shows the data folder the block was given" becomes "an error line that names the data folder, when one was given".
5. Two `.summem/summem note`s, and follow any nap request the tool prints:
   - Every path stockroom writes into shell text is quoted (heredoc, `shlex.quote`, double quotes), so a space or `'` works; rarer characters are out of scope.
   - Nightly entries carry `PATH` and the resolved `STOCKROOM_HOME`, because cron and launchd load no profile, and `schedule status` flags entries that are not up to date.

### 6. Verification

1. **Mutation check M1 to M8:**
   - Extend preflight's `run_r4_variants.py` with M3 and M5 to M7, and re-number M4 (Makefile) as M8.
   - It runs on scratch copies, with its poison stand-ins for `uv`, `crontab` and `launchctl`.
   - Each mutant must turn red exactly its listed set, and the unmutated copy must pass.
2. **BusyBox:** re-run round 3's `busybox_target_check.sh` against the worktree's `SKILL.md`, and expect `PASS`.
3. Run `make ci` from the repo root and read the whole output.
4. Run `claude plugin validate .` and confirm no new warnings.
5. The live shim is baked to `~/git/stockroom`, so the pre-commit `make format` sync of this worktree changes nothing outside it. Confirm with `grep '^# STOCKROOM_' ~/.local/bin/stockroom`.
6. **No live run of cron or launchd.**
   - Cron: this machine's real crontab is not touched. The test runs the entry the way crontab(5) documents.
   - launchd: no macOS host is available. The test runs the plist's argument vector and environment the way launchd.plist(5) documents.
   - The Step 2 live check from round 3 is not re-run. The heredoc and the substitution are unchanged, and only the stderr text changes.

## Technology Validation

No new technology - validation not required.

- `shlex` is in Python's standard library, and `stockroom.shim` already uses it.
- Prefix assignments on a simple command, and double-quoting Make variables in recipes, are plain POSIX shell.
- Every fix was prototyped by the probes under Evidence.

## Dependencies

- cron passes an entry's command part to `/bin/sh -c` in a minimal environment (crontab(5)). launchd runs `ProgramArguments` without a shell, with `EnvironmentVariables` (launchd.plist(5)).
- `/bin/sh` and `make` exist on the test hosts. `make` is already required by `test_coverage_collection.py`, and the Make cases skip without it.
- `stockroom.home.HOME_ENV_VAR` and `resolve_home()`, unchanged.
- Round 3's Step 2 head and owner rules, unchanged.

## Challenges & Mitigations

- **Every installed entry becomes "not up to date" after the update,** because the rendering gains `STOCKROOM_HOME`. A user who re-runs `sr-initialize` is asked once to re-install. Accepted:
  - it is the only way the fix reaches custom-home users who already have an entry;
  - the question is the same in every harness;
  - users who never re-run `sr-initialize` keep today's entry. The PR text tells them to run `stockroom schedule install`.
- **Re-installing can move the nightly job to another warehouse.** For example, the agent's shell has no `STOCKROOM_HOME` while the entry was installed with one. That is why Step 8 tells the user what differs and re-installs only with consent. The `log:` fact shows which home `status` used.
- **A harness that does not load the user's profile,** such as Cursor launched from the macOS Dock, resolves the default home, and Step 8 installs for that. This is unchanged from today, where interactive stockroom commands in that harness use the same home. Out of scope.
- **The quoted entry is hard to read for odd homes.** For a home with a space, `stockroom schedule status` shows `'"'"'`-style quoting. Plain homes differ from today only by the `STOCKROOM_HOME=` assignment. Accepted: the entry is correct, and Step 8 only checks its time and the up-to-date fact.
- **The exact-payload test depends on `tmp_path`.** It holds only characters `shlex.quote` leaves alone (pytest names folders from test names). If that ever changes, the test fails loudly, not silently.
- **The "older" fixtures copy the 2.1.1 rendering.** They are the real format users have installed, written out once. They go red only if status stops flagging that format, not when the current rendering changes.
- **`stub_uv`'s output shares make's stdout** with the echoed recipe lines. Only `UV_`-labelled lines are parsed, and no recipe line starts with `UV_`.
- **Recursive make.** `local-engine` calls `$(MAKE) shim`. A command-line `UV=` passes down through `MAKEFLAGS`, which the probe confirms with 2 calls.
- **zsh is still never run**, here or in CI (carried).

## Pre-Mortem

- **The inventory missed a place, or a variable.** Both inventories name the search used, and preflight re-ran the path search. QA re-runs both. Anything new goes into this round, not a follow-up.
- **The fix lands, but no existing user gets it.** That was the first plan's gap. Unit 2 makes `status` report stale entries, and Step 8 acts on that fact. The PR text covers users who never re-run `sr-initialize`.
- **The tests model cron and launchd, and the real ones behave differently.** Both models follow the documented contract: cron passes the command part to `/bin/sh -c` in a minimal environment, and launchd runs an argument vector with the plist's environment. A real launchd run is not possible here, so QA should read the plist the test writes.
- **Scope creep into contributor tooling.** The Makefile and the hint are contributor-facing. They are in scope because Step 7 sends contributors to `make shim`, which is the same command class, and because the operator's rule is common and breaking. Each fix is a one-word quoting change. If the operator strikes them, Unit 3 drops out whole.
- **The error line adds an expansion that one shell parses differently.** Preflight ran it on the whole fence under dash, bash and BusyBox sh. Verification step 2 re-runs the BusyBox check.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight (PASS WITH ADVISORY, second run)
- [ ] Build
- [ ] QA

## Preflight (first run, c0fc32f): dispositions

- **Finding 1 (FAIL): the nightly job uses the default warehouse.** Fixed with option (a):
  - Unit 1 carries the resolved home as `STOCKROOM_HOME` in both entries, with tests that are red today for all three folders and mutants M3, M5 and M6.
  - Inventory 2 covers the rest of the class. Each variable the engine reads gets a result, and `XDG_CONFIG_HOME` and the source overrides are listed with reasons.
- **Advisory 1 (existing entries are never re-rendered):** applied as Unit 2 (the `up-to-date:` fact) plus Step 8 prose. The plan makes this call so that the fix reaches existing users. Re-installing still needs the user's consent.
- **Advisory 2 (the error line names an install record in Cursor):** applied. The line uses "nothing proves who installed it".
- **Advisory 3 (reuse `stub_uv`):** applied in Unit 3.
- **Advisory 4 (systemPatterns placement):** applied in Unit 5. The cross-cutting paragraph names Step 2 too.
- **Advisory 5 (reuse the mutation runner):** applied in Verification step 1.
- **Advisory 6 (`make shim TAKEOVER=1` with `'` exits 127, not 0):** recorded under Evidence. The call count already catches both.
- **Design idea (`stockroom schedule run`):** not applied.

## Preflight (second run, db85232): PASS WITH ADVISORY, dispositions

Preflight wrote the plan's tests and ran them on `git archive` copies:

- Today's code: the planned 22 failures.
- The planned code: 125 passed, 34 skipped (zsh), 0 failed.
- M1 to M4, M7 and M8 turned red exactly their predicted sets.
- The error line printed the same text in dash, bash and BusyBox sh.

Dispositions:

1. **M5 and M6 turn 4 red each, not 3.** Applied in the mutant table.
2. **On launchd, `status` never shows which home the installed job serves.** Applied: the `entry home:` fact, in the target design, Unit 2's tests and code, and the Step 8 prose.
3. **The `SKILL.md` opening paragraph contradicts Step 8.** Applied in Unit 5.
4. **`schedule install` without `--time` resets the time to 03:30.** Applied in Unit 5's doc text and the PR text.
5. **The troubleshooting doc entry.** Applied in Unit 5.
6. **Put `stub_uv` first on `PATH` in the Make tests.** Applied in Unit 3.
7. **Inventory 2 covers only the engine's own variables.** Applied as a note under Inventory 2 (the `HF_HOME` example).
8. **Minor: the existing status tests read the real `PATH`.** Applied: they pass `fake_which`.
9. **Design idea (session-start `rectify` re-writes a stale entry in place):** not applied.
   - It would write the user's scheduler from a session hook, without consent. The operator decided hooks stay as they are, and Step 8 asks before touching the scheduler.
   - The PR text covers users who never re-run `sr-initialize`. It would add a verb and move the log redirection into Python, and shim refusals on cron would then miss the log. Quoting, plus carrying the home, fixes the defects at lower cost, and Unit 2 gives the stale-entry check without it.
