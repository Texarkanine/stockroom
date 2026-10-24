# Task: warehouse-file-growth, milestone 7 (session-start launch)

* Task ID: warehouse-file-growth
* Complexity: Level 2
* Type: simple enhancement

Start the check pass from the Claude Code and Cursor session-start hooks. The hook command returns at once. The launch detaches the way `stockroom dashboard` does: a new session, and the child keeps none of the hook's output streams. Cursor's `beforeSubmitPrompt` hook does not launch the check. There is no new user-facing command. The pass in `stockroom.check` stays as it is.


## Test Plan (TDD)

### Behaviors to Verify

- Final record: with `PYTHONPATH` set to the engine `src` directory, `launch` on a `generations_file` home whose record is `swapped` for this check version → the child exits 0, the record stays `swapped`, and `warehouse.copy.duckdb` is not created
- Missing home: with that same `PYTHONPATH`, `launch` on a path that is not a directory → the child exits 0 and the path is still absent
- Alarm stays in the child: with that same `PYTHONPATH`, after `launch` returns, `signal.alarm(0)` in the parent is 0
- No user-facing command: `python -m stockroom check` → exit 2, the token `check` named on stderr, no traceback
- Hook entry: `python -m stockroom.check` with no arguments calls `launch` with `resolve_home()` and does not call `entry` in that process
- Claude session start: the one `SessionStart` command contains `-m stockroom.check` after `shim rectify`, still runs on-path `stockroom dashboard`, and still silences stderr
- Cursor session start: the one `sessionStart` command contains `-m stockroom.check` after `shim rectify`, still runs on-path `stockroom dashboard`, and still leaves stderr visible
- Cursor prompt submit: the `beforeSubmitPrompt` command does not contain `stockroom.check`
- New install: a home with no warehouse, empty transcript roots, `STOCKROOM_AI_TRACKING_DB` pointed at a missing file, and `PYTHONPATH` set to the engine `src` directory → `ingest` creates a schema-file warehouse, `embed` and `semantic` exit 0 through `FakeEncoder`, and `launch` records `already-new` and does not create `warehouse.copy.duckdb`

### Test Infrastructure

- Framework: pytest
- Test location: `skills/sr-search/tests/`
- Conventions: one behavior per test, docstring states the behavior, homes are `tmp_path` or a fixture copy, subprocess CLI tests use `sys.executable -m`
- New test files: none

## Implementation Plan

### 1. Detached launch — executable

- Files: `skills/sr-search/src/stockroom/check.py`, `skills/sr-search/tests/test_check.py`, `skills/sr-search/tests/test_dispatcher_cli.py`

1. Stub tests: in `test_check.py`, empty tests for the final-record launch, the missing home, the parent alarm, and the no-argument module entry. In `test_dispatcher_cli.py`, an empty test that `check` is not a subcommand.
2. Stub interface: in `check.py`, add `launch(home: Path) -> subprocess.Popen` and `main(argv: list[str] | None = None) -> int`, with docstrings and no body. `main` accepts `--foreground` and an optional home path. No `SUBCOMMANDS` entry.
3. Write tests and run red. Before every `launch` call, `monkeypatch.setenv("PYTHONPATH", ...)` to the engine `src` directory, using the same `_SRC` value as `test_entry_alarm_kills_a_stuck_copy` (`Path(stockroom.__file__).resolve().parent.parent`). `launch` inherits that environment. Do not pass an `env` argument.
    - Final record: copy nothing yourself. Use the `generations_file` fixture, `write_record` a `{"check_version": 1, "status": "swapped"}` record, call `launch(home)`, and `wait` on the returned process with a timeout. Assert exit 0, the record is unchanged, and `storage.COPY_FILENAME` is absent.
    - Missing home: `launch` a path under `tmp_path` that was never created. Assert the child exits 0 and the path does not exist.
    - Parent alarm: call `launch` on the final-record home, then assert `signal.alarm(0)` returns 0 before waiting for the child.
    - Module entry: monkeypatch `launch` to record the path and return a finished stand-in, monkeypatch `entry` to raise, set `STOCKROOM_HOME` to a tmp home, and run `main([])`. Assert `launch` received `resolve_home()`'s path and `entry` was not called.
    - Dispatcher: `python -m stockroom check` exits 2, stderr names `check`, and stderr has no traceback.
4. Write code and run green:
    - `launch` starts `[sys.executable, "-m", "stockroom.check", "--foreground", str(home)]` with `stdin`, `stdout`, and `stderr` set to `DEVNULL`, `start_new_session=True`, and `close_fds=True`. It passes no `env`, so the child inherits the parent environment, including the `PYTHONPATH` the hook sets and the tests set. It returns the `Popen` and does not wait. It does not call `entry` or `home_dir`. It does not bake a source-tree path of its own.
    - `main` with `--foreground` calls `entry` on the given home, or on `resolve_home()` when the home argument is omitted, then returns 0.
    - `main` without `--foreground` calls `launch` on that same home and returns 0 without waiting.
    - `if __name__ == "__main__"` raises `SystemExit(main())`.
    - Do not add `check` to `SUBCOMMANDS`. Do not change `entry` or `run_check`.

### 2. Session-start commands — executable

- Files: `hooks/claude-hooks.json`, `hooks/cursor-hooks.json`, `skills/sr-search/tests/test_packaging.py`

1. Stub tests: extend the Claude and Cursor session-start tests, and the `beforeSubmitPrompt` test, with empty assertions for the check command.
2. Stub interface: none. The command text is the interface.
3. Write tests and run red:
    - Both session-start commands contain the exact token `-m stockroom.check` after `shim rectify` and after `stockroom dashboard`.
    - The check invocation is `"$PY" -m stockroom.check` with `PYTHONPATH` set, and it does not use `uv run`.
    - `_assert_combined_rectify_then_dashboard` still bans `PYTHONPATH=` and `python -m stockroom` on the dashboard command only. Bound that slice at the next `;`, so a later command is not part of the dashboard launch.
    - The `beforeSubmitPrompt` command does not contain `stockroom.check`. Its existing continue, path-only, and background assertions stay.
4. Write code and run green: inside the existing `{ ... }` group, after `stockroom dashboard` and still before `|| true`, add `PYTHONPATH="$APP/src" "$PY" -m stockroom.check`. Claude keeps `>/dev/null 2>&1`. Cursor session start keeps `>/dev/null` and does not gain `2>&1`. Do not add `&`. Do not change `beforeSubmitPrompt`.

### 3. New-install proof — executable

- Files: `skills/sr-search/tests/test_check.py`

1. Stub tests: one empty test for the empty-home install.
2. Stub interface: none. This test calls `ingest`, `embed.main`, `semantic.main`, and `launch`.
3. Write tests and run red: under `tmp_path`, set `STOCKROOM_HOME` to a new directory and point `STOCKROOM_CURSOR_ROOT`, `STOCKROOM_CURSOR_CHATS_ROOT`, `STOCKROOM_CLAUDE_ROOT`, and `STOCKROOM_AI_TRACKING_DB` at paths inside `tmp_path`. The tracking path is a missing file. Set `PYTHONPATH` to the same `_SRC` directory before `launch`. Run `ingest`. Assert `warehouse.duckdb` exists. Run `embed.main` and `semantic.main` with `encoder_factory=FakeEncoder` and a non-empty semantic query. Both return 0. Call `launch` on that home, wait for the child, and assert the record status is `already-new` and `storage.COPY_FILENAME` does not exist.
4. Write code and run green: no production change. The test goes green on the launch from step 1 and the existing ingest, embed, and semantic functions.

### 4. Hook description — prose/policy

- Files: `docs/user-guide/troubleshooting/index.md`, `docs/user-guide/quickstart.md`, `docs/user-guide/dashboard.md`, `docs/user-guide/load/schedule.md`, `docs/user-guide/installed-layout.md`, `docs/architecture/lifecycle.md`, `docs/architecture/index.md`, `memory-bank/systemPatterns.md`
- No tests: prose/policy artifact

1. In the troubleshooting Warehouse section, before the rename steps, say that session start runs this check. The first run rehearses a copy and deletes that copy. A later session start replaces `warehouse.duckdb` with a verified copy and keeps the original as `warehouse.issue147-swap.duckdb`. Leave the four rename steps as they are.
2. In the quickstart dashboard bullet, say that session start also runs this check, in those same two beats.
3. In `dashboard.md`, say that session start also starts the check, and that `beforeSubmitPrompt` does not.
4. In `docs/user-guide/load/schedule.md`, keep the statement that session-start hooks do not ingest or embed. Replace "they only heal the shim and launch the dashboard" so the sentence also says they start the detached check.
5. In the `hooks/` row of `docs/user-guide/installed-layout.md`, keep that those hooks do not ingest or migrate. Say session start also starts the detached check, and that `beforeSubmitPrompt` does not.
6. In `lifecycle.md`, say session start does three things. The third is the detached check, and the hook does not wait for it. Session start still does not ingest, embed, or migrate.
7. In the architecture index Pieces list, include the check in the Hooks bullet.
8. In `systemPatterns.md`, say session start also starts the check, detached, and `beforeSubmitPrompt` does not.

## Technology Validation

No new technology - validation not required

## Dependencies

- `stockroom.check.entry` and `run_check` from milestone 6
- `stockroom.home.resolve_home` for the hook's default home. `launch` must not call `home_dir`
- `dashboard.spawn` is the pattern for the `Popen` flags. Do not import the dashboard package
- `FakeEncoder` in `skills/sr-search/tests/conftest.py` for the new-install proof
- `generations_file` for a warehouse the pass would copy if the final record did not stop it

## Challenges & Mitigations

- A bare `&` in the Cursor session-start command can hold the hook until the 300-second timeout, because that command discards stdout and leaves stderr open. The child is started with `DEVNULL` on all three streams and `start_new_session=True`. The command does not use `&`.
- A `stockroom check` subcommand would show up in `stockroom --help`. The hook runs `python -m stockroom.check`. The dispatcher test locks the absence of that subcommand.
- `entry` sets `SIGALRM` in the process that calls it. Only the `--foreground` child calls `entry`. The parent test asserts the alarm is unset.
- `home_dir()` creates a missing home. The no-argument path uses `resolve_home()`, and a missing directory stays missing.
- `ingest` with no root overrides reads this machine's transcripts and tracking databases. The new-install test points every root, including `STOCKROOM_AI_TRACKING_DB`, under `tmp_path`.
- The check has to run on the interpreter rectify just ensured. It uses the same `"$PY"` and `PYTHONPATH` as rectify, inside the same group, after rectify. It does not use `uv run` or a bare `python3`.
- pytest's `pythonpath` does not reach a child, and `uv run` does not set `PYTHONPATH`. The child's stderr is `DEVNULL`, so a missing import looks like a non-zero exit. Every test that waits on `launch` sets `PYTHONPATH` to `_SRC` first. `launch` inherits the environment and does not grow a source-tree path.
- `check.py` imports DuckDB at import time, so the hook parent waits for that import before it spawns. Moving those imports would edit `entry` and `run_check`. That advisory stays out of this plan.
- This milestone turns the rehearsal and the swap on for every install that updates. That is the deliverable. The launcher does not add a second lock or a second record.

## Pre-Mortem

- The hooks gained the command string, and the behavioral test never ran the process that string starts. Step 1 waits on the child `launch` starts, which is `python -m stockroom.check --foreground`, with `PYTHONPATH` set so that child can import `stockroom`. Step 2 asserts that exact `-m stockroom.check` token in both session-start commands.
- The new-install proof called the real encoder and the suite then required torch. The plan injects `FakeEncoder` and expects no production change in that step.
- The launch was folded into `entry` or `run_check`, so doctor, tests, and in-process callers started spawning children. `launch` and `main` are new. `entry` and `run_check` stay as they are.
- The dashboard-command bans in `_assert_combined_rectify_then_dashboard` treated everything after the word `dashboard` as the dashboard launch, so the check command was shoved in front of the dashboard to keep the slice green. The plan bounds that slice at the next `;` and puts the check after `stockroom dashboard`.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Unit 1 detached launch
- [x] Unit 2 session-start commands
- [x] Unit 3 new-install proof
- [x] Unit 4 hook description
- [x] Build
- [x] QA

## QA

PASS. The session-start launch is acceptable as-is.

- Launch: `launch` starts `python -m stockroom.check --foreground` with discarded streams, a new session, and `close_fds=True`. It passes no `env` and returns the `Popen`. `main` uses `resolve_home()`'s path when the home argument is omitted. `--foreground` calls `entry`. The other path calls `launch` and returns 0. `entry` and `run_check` are unchanged. `check` is not a subcommand.
- Hooks: both session-start commands run `PYTHONPATH="$APP/src" "$PY" -m stockroom.check` after `stockroom dashboard` and `shim rectify`, inside the group, with no `&`. Claude keeps `>/dev/null 2>&1`. Cursor session start keeps `>/dev/null`. `beforeSubmitPrompt` does not contain `stockroom.check`.
- New install: the test points the four roots under `tmp_path`, uses `FakeEncoder`, and expects `already-new` with no `warehouse.copy.duckdb`.
- Docs: troubleshooting states the rehearsal, the deleted copy, and the later swap under `warehouse.issue147-swap.duckdb`. The four rename steps are unchanged. Quickstart, dashboard, schedule, installed layout, lifecycle, the architecture index, and the hooks paragraph in `systemPatterns.md` say session start starts the detached check. Where the plan asked, they say `beforeSubmitPrompt` does not.
- Advisory. The hook parent imports DuckDB before it spawns, because `launch` lives in `check.py`. The plan left that split out. Acceptable as-is.
- Advisory. The lifecycle doctrine still calls a repeated session start a no-op when already healthy, and says stdout and stderr are discarded. The check rehearses, then later replaces the warehouse. Cursor session start leaves stderr visible. The session-start section states the check. Acceptable as-is.
- Advisory. The opening of `systemPatterns.md` still describes session start as rectify and the dashboard. The hooks paragraph includes the detached check. The architecture index and packaging still say every caller goes through the shim. Lifecycle says the check does not. Preflight left those two sentences. Acceptable as-is.
