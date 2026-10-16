# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

**Rework round 1: fix the PR #142 review findings.** The first pass (plan, Build, QA PASS, Reflect) shipped on this branch at 7f3917f; its plan and history are in git and in `progress.md`. Six bot inline comments on PR #142 were judged valid and reproduced at that head, and the operator asked for all of them to be fixed. This round fixes four defects:

- **Step 2 labels some checkouts with a harness.** A checkout under any folder named `synced` (r4299336743, r4299392123), or three levels below any folder named `cache` (r4299336751), gets `OWNER=claude` under `claude --plugin-dir`. The cache case gets an empty `OWNER` otherwise, and the prose then tells the agent to name its harness.
- **Step 7's mislabel row omits synced copies** (r4299336757).
- **`shim rectify` crashes on an uncheckable foreign engine dir** (r4299336767). `_alive` uses `Path.is_file()`, which raises `PermissionError` (and ESTALE, EIO, …) on Python 3.11 to 3.13. `rectify` then exits 1 with a traceback instead of 0. Python 3.14 instead returns `False`, which would count the engine as dead and replace the shim. `install` has the same crash, and it predates this PR.
- **The printed Step 2 line is not valid shell when a path contains `'`** (r4299392136).

### Operator decisions (2026-10-16)

- **Contributors always get `dev`.** A marketplace install must be recognizable as a real install. Anything run from a checkout with intent to develop or iterate is `dev`. That covers `claude --plugin-dir`, Cursor `~/.cursor/plugins/local/`, local-path marketplaces loaded in place, and the Cursor localdev mirror.
- **Hooks stay as they are.** Option B, `rectify` doing nothing on dev loads, is rejected: a dev session's hook must still be able to heal the checkout.
- **`rectify` replaces a dead shim, whoever owns it.** This is approved. It makes the operator's model true: break or remove your dev shim, and the next session of the real install brings it back.
- **No separate dev data (option E rejected).** Dev intentionally runs checkout code against the real warehouse, after a backup.
- **Argument substitution is not a concern.** None of our skills take arguments. No argument test and no hygiene guard; the Step 2 block simply uses no positional tokens.
- **Option A, the install-layout rule, is for `sr-initialize` only.** Hooks are the real-install signal for themselves; `sr-initialize` runs with no hook, so it needs the rule.
- **PR #142 review (2026-10-16): fix all six findings in this PR.**
- **No Claude-driven questions for Cursor users (2026-10-16):** "We do not want Cursor users to have to answer extra questions to account for Claude Code situations." Cursor's Step 2 path must keep its first-pass outcomes; any new question may reach Claude Code users only.

### Owner rule for this round

**The path decides inside a harness's default plugins folders. Outside them, Cursor keeps its first-pass evidence, and only Claude Code asks the user.** The judge recommended asking for r4299336751, the operator answered "fix all of those", and then limited the question to Claude Code. The rule:

- `claude`: `…/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` and `…/.claude/plugins/synced/…`. `cursor`: `…/.cursor/plugins/cache/<marketplace>/<plugin>/<version>/`. The path alone decides.
- A copy laid out like an install (`<x>/cache/<m>/<p>/<v>/skills/sr-search`) anywhere else:
  - `CURSOR_PLUGIN_ROOT` physically holds this engine → `cursor`. This is unchanged from the first pass.
  - Otherwise `OWNER` is empty:
    - **In Claude Code**, the agent asks the user whether `APP_DIR` is a checkout they develop in (`dev`) or a plugin installed under a custom folder (`claude`).
    - **In any other harness**, the agent sets `OWNER` to the harness it is running in, with no question. This is unchanged from the first pass.
- Everything else is `dev`.

Why Claude Code asks: `claude --plugin-dir` substitutes the checkout as `${CLAUDE_PLUGIN_ROOT}`, exactly as a real install does. So substitution cannot tell a custom-root install from a checkout that happens to sit in a `cache/<a>/<b>/` shape, and the block stops reading `${CLAUDE_PLUGIN_ROOT}`. Labelling a copy `dev` by mistake fails safe, because Step 7 tells the agent to stop and ask when `APP_DIR` is not the user's checkout. Labelling a copy with a harness by mistake fails silently.

Cost, stated plainly: Claude Code users with `CLAUDE_CONFIG_DIR` or `CLAUDE_CODE_PLUGIN_CACHE_DIR` set are asked one question during `sr-initialize`. Before this round, substitution labelled them automatically, which the first pass verified end to end. Cursor users see no new question.

Accepted residual (Cursor): a checkout whose real path has a `cache/<a>/<b>/` shape, with SKILL.md read through that real path (not the `plugins/local` link), and no `CURSOR_PLUGIN_ROOT`, still gets `cursor` from the agent. It is the Cursor form of r4299336751, and catching it would need the question the operator ruled out.

Fallback if the operator or preflight rejects the Claude question: keep substitution as proof, but only under a `…/plugins/cache/<m>/<p>/<v>` shape. Then only `CLAUDE_CODE_PLUGIN_CACHE_DIR` roots not named `plugins` get the question.

### Evidence that shaped the plan

- **Claude Code docs:**
  - [plugins reference, Environment variables](https://code.claude.com/docs/en/plugins-reference#environment-variables): plugin path variables resolve inline in hook `command` and are exported to hook, MCP stdio and LSP processes. They "aren't present in the environment of commands Claude runs through the Bash tool".
  - [skills, string substitutions](https://code.claude.com/docs/en/skills#available-string-substitutions): in skill content, Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` (plugin skills) and `${CLAUDE_SKILL_DIR}` at load.
  - [plugin loading](https://code.claude.com/docs/en/plugins/loading): marketplace installs are copied to `<plugins root>/cache/<marketplace>/<plugin>/<version>/`, and `${CLAUDE_PLUGIN_ROOT}` points there. The plugins root is `~/.claude/plugins` unless `CLAUDE_CODE_PLUGIN_CACHE_DIR` is set. `--plugin-dir` and local-path marketplace plugins load in place. A `--plugin-dir` copy silently replaces a same-named installed plugin for that session, so only the checkout's hooks run. Old version directories are removed 14 days after an update or uninstall.
- **Probe on Claude Code 2.1.301**, run headless with a throwaway plugin and a project skill:
  - In plugin skills, `${CLAUDE_PLUGIN_ROOT}` is substituted, including inside quotes and code fences.
  - Bare `$CLAUDE_PLUGIN_ROOT`, `${CLAUDE_PLUGIN_ROOT:-x}` and `${CURSOR_PLUGIN_ROOT}` stay literal.
  - In project skills, `${CLAUDE_PLUGIN_ROOT}` stays literal and `${CLAUDE_SKILL_DIR}` is substituted. Neither has a trailing slash.
  - A second preflight probe found that `$ARGUMENTS` and `$N` are substituted when a skill gets arguments. Not a concern per the operator.
- **Bash tool on 2.1.301**: no `*_PLUGIN_ROOT` in the environment. The warehouse shows the same in July 2026 (plugin 0.1.1); that agent quietly improvised `OWNER=claude`.
- **Cursor:**
  - Docs cover `${CURSOR_PLUGIN_ROOT}` expansion only in MCP config.
  - Forum staff endorse `${CURSOR_PLUGIN_ROOT}` in `hooks.json`, and hook processes receive both variables (a reported CLI bug can leak another plugin's root into nested children).
  - Nothing documents the variables in agent shells or substitution in skill text.
  - Marketplace installs on this machine live at `~/.cursor/plugins/cache/<marketplace>/stockroom/<sha>/`, the same three-level shape as Claude's. Cursor's documented plugin-development folder is `~/.cursor/plugins/local/`.
- **Install dirs** contain `.git` **and** `Makefile` in both harness caches. So "checkout markers → dev" would misfire. It also means an agent that followed today's "defer to `make shim` from the repo root" inside a plugin cache succeeds, leaving a `dev` shim baked to the cache.
- **Hooks audit:** both hooks expand the root in the hook's own shell and pass it as `--app-dir`, and `claude plugin validate .` passes. Under the documented dev flow, the checkout's hooks find a `dev` shim and leave it alone. A `claude`-labelled checkout shim, from launching `--plugin-dir` before `make shim`, is rebaked back by the real install's hook once it returns. The every-prompt Cursor hook runs the same `rectify`, so it adds no new failure class. Result: no hook change.
- **The one real stuck path:** a `dev` shim whose checkout is gone (deleted worktree, moved clone). `rectify` never touches another owner, even a dead one, and the shim's remedy says "run 'make shim' from your stockroom checkout". This happened on this machine (dead worktree `stockroom-cursor-subagents`).
- **Review reproductions (2026-10-16, at 7f3917f, dash and bash):**
  - `--plugin-dir` checkout at `projects/synced/stockroom` → `OWNER='claude'`; at `projects/stockroom` → `dev`.
  - `--plugin-dir` checkout at `src/cache/acme/widgets/stockroom` → `OWNER='claude'`; the same path with the placeholder filled → `OWNER=''` plus "the harness did not say which".
  - Running the printed line for `…/O'Brien/stockroom` → `Syntax error: Unterminated quoted string`.
  - Real `python -m stockroom shim rectify --path-only --owner claude` against a `dev` shim baked under a mode-000 folder → `PermissionError` traceback, exit 1, shim unchanged. `Path.is_file()` raises there on 3.11.13, 3.12.11 and 3.13.7; 3.14.0rc3 returns `False`.
  - The hooks wrap `rectify` in `{ …; stockroom dashboard; } >/dev/null 2>&1 || true`, so users see nothing. The CLI still breaks its documented exit-0 contract.
  - This machine's `~/.claude/plugins/synced/<bucket>/` holds no plugins, so the planned `synced/<bucket>/<plugin>` depth is not confirmed locally. The new rule matches `*/.claude/plugins/synced/*` and does not depend on that depth.
- **Prototypes (2026-10-16, scratch):**
  - The target Step 2 block below (revision with the Cursor lines kept) gave the planned `OWNER` and round-tripped `APP_DIR` through the printed line in all 15 modeled cases under dash and bash. Those cases include Cursor custom cache with env → `cursor`, and a leaked Cursor root on a Claude custom root → empty. The `O'Brien files` case also passes under busybox sh.
  - The target `_alive` gave gone → dead, no `pyproject.toml` → dead, and mode-000 parent → alive on Python 3.11, 3.13 and 3.14.

### Target design

**Step 2 block** (replaces the fence that assigns `SKILL_DIR=`; no functions, no positional tokens; the `${CLAUDE_PLUGIN_ROOT}` read is removed, the `${CURSOR_PLUGIN_ROOT}` read stays):

```bash
SKILL_DIR="${CLAUDE_SKILL_DIR}"
[ -n "$SKILL_DIR" ] || SKILL_DIR="<POSIX absolute path of the directory holding this SKILL.md>"
APP_DIR="$(CDPATH='' cd -- "$SKILL_DIR/../sr-search" 2>/dev/null && pwd)"
PLUGIN_ROOT="${APP_DIR%/skills/sr-search}"
CACHE_DIR="${PLUGIN_ROOT%/*/*/*}"
REAL_APP="$(CDPATH='' cd -P -- "$APP_DIR" 2>/dev/null && pwd)"
CURSOR_APP=""
[ -z "${CURSOR_PLUGIN_ROOT}" ] || CURSOR_APP="$(CDPATH='' cd -P -- "${CURSOR_PLUGIN_ROOT}/skills/sr-search" 2>/dev/null && pwd)"
OWNER=""
if [ ! -f "$APP_DIR/pyproject.toml" ]; then
  printf 'sr-initialize: no stockroom engine beside %s\n' "$SKILL_DIR" >&2
  APP_DIR=""
elif [ "$PLUGIN_ROOT" != "$APP_DIR" ] && [ "${CACHE_DIR##*/}" = cache ]; then
  case "$APP_DIR" in
    */.claude/plugins/cache/*) OWNER=claude ;;
    */.cursor/plugins/cache/*) OWNER=cursor ;;
    *)
      if [ -n "$CURSOR_APP" ] && [ "$CURSOR_APP" = "$REAL_APP" ]; then OWNER=cursor
      else printf 'sr-initialize: %s is laid out like an installed plugin, but not in a default plugins folder\n' "$APP_DIR" >&2
      fi ;;
  esac
else
  case "$APP_DIR" in
    */.claude/plugins/synced/*) OWNER=claude ;;
    *) OWNER=dev ;;
  esac
fi
printf "APP_DIR='%s'; OWNER='%s'\n" "$(printf '%s' "$APP_DIR" | sed "s/'/'\\\\''/g")" "$OWNER"
```

The `sed` turns each `'` into `'\''`. `OWNER` is always one of `claude`, `cursor`, `dev` or empty, so it needs no escaping.

**`_alive` (`stockroom.shim`):** stat `pyproject.toml` directly. Dead means `ENOENT`, `ENOTDIR` or `ELOOP` (the "is not there" answers `Path.is_file` ignored before 3.14), or a non-regular file. Any other `OSError` means the engine could not be checked, and that counts as alive. Then `rectify` does nothing (exit 0, shim untouched) and `install` refuses unless `--takeover --force`. The refusal wording stays unchanged.

**Step 7:** the mislabel row also matches a claude.ai-synced copy (`…/.claude/plugins/synced/…`). The table gets a row for an engine directory the agent cannot check: tell the user, and offer `--takeover --force` only with explicit consent.

## Test Plan (TDD)

### Behaviors to Verify

**Step 2 block** (`test_initialize_context.py`; each case runs under `sh`, `bash` and `zsh` where installed):

- Every case reads `OWNER` and `APP_DIR` back by running the block's printed line in a fresh shell, not from the block's own variables. That printed line is the interface the agent actually uses.
- **Path with `'` and a space** (checkout at `<tmp>/O'Brien files/stockroom`, Claude rendering) → the printed line runs and gives `("dev", <root>/skills/sr-search)`. Red today: the printed line does not parse.
- **`--plugin-dir` checkout under a `synced/` folder** (`<tmp>/projects/synced/stockroom`, checkout tree, Claude rendering) → `dev`. Red today: `claude`.
- **`--plugin-dir` checkout in a cache-shaped path** (`<tmp>/src/cache/acme/widgets/stockroom`, checkout tree, Claude rendering) → `OWNER` empty, `APP_DIR` resolved. Red today: `claude`.
- **Claude custom plugins root** (`<tmp>/plugin-root/cache/txrk9/stockroom/2.1.1`, Claude rendering) → `OWNER` empty, `APP_DIR` resolved. Red today: `claude`. This changes an existing case.
- **Leaked `CURSOR_PLUGIN_ROOT` on a Claude custom root** (the root points at another plugin's engine) → `OWNER` empty: neither `claude` nor `cursor`. Red today: `claude`. This changes an existing case.
- Unchanged and still green (regression guards):
  - Claude marketplace, with and without substitution → `claude`.
  - Claude synced copy under `~/.claude/plugins/synced/bucket-1/stockroom` → `claude`.
  - Cursor marketplace → `cursor`.
  - Cursor custom cache with `CURSOR_PLUGIN_ROOT` holding this engine → `cursor`. This guards the operator's "no new Cursor questions" decision.
  - `--plugin-dir` checkout, local marketplace in place, Cursor `plugins/local` → `dev`.
  - Cursor localdev mirror, and the mirror in a `cache`-named folder → `dev`, with the logical mirror path.
  - Unattributed cache copy (agent fill, no env) → `OWNER` empty.
  - Missing engine, unfilled placeholder → both empty.

**`_alive` through `rectify` and `install`** (`test_shim.py`):

- **`rectify`, foreign shim whose engine dir cannot be checked** (a `dev` shim baked at a dir whose parent is then `chmod 000`) → `action == "noop"`, dest unchanged, no exception. Red today: `PermissionError`.
- **`install` by another owner over that shim**, with and without `--takeover` → `action == "refused"`, dest unchanged, no exception. Red today: `PermissionError`.
- Unchanged and still green: a dead foreign shim (folder without `pyproject.toml`) is replaced by `rectify` and needs `--takeover` in `install`; a live foreign shim is a `rectify` noop and needs `--takeover --force` in `install`; a corrupt header is foreign; an unidentified file is a `rectify` noop.

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`
- Conventions:
  - `test_initialize_context.py`: a module docstring stating the owner rule, per-test docstrings, the `shell` / `step2` / `home` fixtures, and the `_render_claude` / `_fill_placeholder` / `_run_block` helpers. `subprocess.run` runs with an explicit minimal env.
  - `test_shim.py`: classes `TestInstall` / `TestRectify`, and the `engine_dir` / `other_engine_dir` / `dead_dir` / `dest` fixtures. `TestRectify` stubs `ensure_engine_env`, and `no_dest_on_path` skips the PATH verify.
- New test files: none

## Implementation Plan

### 1. `_alive` counts an uncheckable engine as alive — executable

- Files: `skills/sr-search/tests/test_shim.py`, `skills/sr-search/src/stockroom/shim.py`

1. Stub tests:
   - Add a module-level fixture `uncheckable_dir(tmp_path)`. It builds an alive engine dir at `tmp_path / "locked" / "engine"` and yields it. The fixture itself does no `chmod`. Its teardown restores mode `0o755` on `locked`, so tmp cleanup works.
   - Add a small helper `_lock(path)` that sets `chmod 000` on `path.parent`. The tests call it after installing, because installing needs a readable dir.
   - Mark both new tests `skipif(os.geteuid() == 0)`: root ignores the mode bits.
   - Add `TestRectify.test_foreign_shim_with_uncheckable_engine_left_untouched` and `TestInstall.test_foreign_owner_uncheckable_dir_refuses_untouched`, empty and documented.
2. Stub interface: none (the `_alive` signature is unchanged).
3. Write tests and run red:
   - rectify: `shim.install(dest, uncheckable_dir, "dev")`, `_lock(uncheckable_dir)`, `shim.rectify(dest, engine_dir, "claude")` → `noop` and `dest.read_text()` unchanged.
   - install: same setup; `shim.install(dest, engine_dir, "claude")` and `shim.install(..., takeover=True)` → both `refused` and dest unchanged.
   - Run `pytest tests/test_shim.py -n0`. Both new tests fail with `PermissionError` on the local Python 3.13.
4. Write code and run green:
   - In `shim.py`, add `import errno` and `import stat`, and a constant `_GONE_ERRNOS = frozenset({errno.ENOENT, errno.ENOTDIR, errno.ELOOP})`.
   - `_alive` becomes `try: return stat.S_ISREG((Path(app_dir) / "pyproject.toml").stat().st_mode)` / `except OSError as exc: return exc.errno not in _GONE_ERRNOS`. Its docstring says why it avoids `Path.is_file` (its behavior differs across Python versions) and that "could not check" counts as alive, so nothing is overwritten unseen.
   - Update the `rectify` docstring bullets to say an uncheckable engine counts as alive.
   - Re-run `pytest tests/test_shim.py tests/test_shim_cli.py -n0` until green.

### 2. Step 2: default-folder owner rule and a shell-safe printed line — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests:
   - Module docstring: restate the owner rule. The path decides in the default plugins folders (`…/.claude/plugins/cache/…`, `…/.claude/plugins/synced/…`, `…/.cursor/plugins/cache/…`). An install-shaped copy elsewhere is `cursor` when `CURSOR_PLUGIN_ROOT` holds it; otherwise it gets no owner. Claude Code's substituted plugin root is not proof, because `--plugin-dir` substitutes a checkout too. Everything else is `dev`. Also state that every case reads back through the printed line.
   - Add empty, documented tests: `test_printed_line_survives_quotes_in_the_path`, `test_claude_plugin_dir_checkout_under_synced_is_dev`, `test_checkout_in_a_cache_shaped_path_gets_no_owner`.
   - Modify existing tests (always-tdd stubbing step 3):
   - Rework `_run_block`. Run the block; assert stdout has exactly one line starting with `APP_DIR=`; run that line plus `printf "%s\n%s\n" "$OWNER" "$APP_DIR"` in a fresh process of the same shell; return the last two lines. Update its docstring.
   - Rename `test_claude_custom_plugins_root` to `test_claude_custom_plugins_root_gets_no_owner`. Expect `("", <root>/skills/sr-search)`. Docstring: `--plugin-dir` substitutes a checkout the same way, so substitution is not proof.
   - `test_cursor_custom_cache_with_env`: no change. It must stay green.
   - `test_leaked_cursor_root_is_ignored`: expect `("", <root>/skills/sr-search)`. Docstring: a `CURSOR_PLUGIN_ROOT` that holds some other plugin labels nothing, and a Claude custom root gets no owner.
   - `test_unattributed_install_has_no_owner`: expectation unchanged. Docstring: the agent names its harness, or in Claude Code asks the user.
2. Stub interface: none. The interface is the Step 2 fence, and the tests run against the current block first.
3. Write tests and run red:
   - Implement the three new tests per the behaviors above.
   - Run `pytest tests/test_initialize_context.py -n0`. The red set: the quotes case, the synced checkout, the cache-shaped checkout, the Claude custom root and the leaked Cursor root, under every installed shell. Everything else stays green, which shows the reworked `_run_block` reads current behavior correctly.
4. Write code and run green:
   - Replace the Step 2 fence in `SKILL.md` with the target block, verbatim.
   - Rewrite the owner bullets above the block. `claude` / `cursor` means a copy in that harness's default plugins folder: the cache paths, plus `~/.claude/plugins/synced/…` for claude.ai-synced copies. A Cursor install in a custom folder also counts when Cursor exports its plugin root. The `dev` bullet is unchanged.
   - The intro sentence: Claude Code writes this skill's directory into the block (drop "and plugin root").
   - The printed-line paragraph: copy it exactly; it is already quoted for the shell.
   - The empty-`OWNER` bullet branches by harness:
     - In Claude Code: ask the user whether `APP_DIR` is a checkout they develop in (`dev`) or a plugin installed in a custom plugins folder (`claude`), then set `OWNER` in the printed line. Never pick it yourself.
     - In any other harness: keep the first-pass text, which is to set `OWNER` to the harness you are running in.
   - Re-run until green under every installed shell. Also run `grep -n 'CLAUDE_PLUGIN_ROOT}' skills/sr-initialize/SKILL.md` and confirm it finds nothing; the `CURSOR_PLUGIN_ROOT` read stays. This is a one-off check, not a test.

### 3. Step 7: synced row and uncheckable engines — prose/policy

- Files: `skills/sr-initialize/SKILL.md`
- No tests: prose/policy artifact

1. In the liveness sentence, add: if checking that directory fails with any error other than "No such file or directory" (for example "Permission denied"), it cannot be checked.
2. Mislabel row: "inside a marketplace install (`…/cache/<marketplace>/<plugin>/<version>/…`, or a claude.ai-synced copy under `…/.claude/plugins/synced/…`)". Change "a plugin update removes that directory" to "a plugin update can remove that directory".
3. Add a row: "Another owner, engine cannot be checked". The agent tells the user what the shim points at and why it cannot tell. It offers `--takeover --force` only with explicit consent; otherwise it leaves the shim. This matches `install`, which now refuses such a shim unless both flags are passed.
4. Dev-branch bullets: no change. `make shim TAKEOVER=1` is for a dead shim only. The uncheckable case goes to the user like the live one.

### 4. Shared patterns and repository memory — prose/policy

- Files: `memory-bank/systemPatterns.md`, `.summem/notes/*` (through `.summem/summem note` only)
- No tests: prose/policy artifact

1. `systemPatterns.md`, "Dual-manifest plugin" paragraph: "A real install is…" becomes "`sr-initialize` labels a copy by path inside a harness's default plugins folder (`…/.claude/plugins/cache|synced/…`, `…/.cursor/plugins/cache/…`). Elsewhere, an install-shaped copy is `cursor` when `CURSOR_PLUGIN_ROOT` holds it. Otherwise Claude Code asks the user and other harnesses name themselves. Every other load is `dev`. The substituted `${CLAUDE_PLUGIN_ROOT}` is not proof, because `--plugin-dir` substitutes a checkout too." Keep the test pointer.
2. `systemPatterns.md`, "Baked-only" paragraph: "a dead shim" stays. Add "(engine verifiably gone; an engine that cannot be checked counts as alive)".
3. `.summem/summem note` with two facts:
   - The Step 2 owner rule: the path decides in the default folders; elsewhere `CURSOR_PLUGIN_ROOT` decides `cursor`; otherwise only Claude Code asks the user. This supersedes the 2026-10-16 owner note.
   - `_alive`: only ENOENT, ENOTDIR and ELOOP mean dead, because `Path.is_file` differs on 3.13 and 3.14.
   - Follow any nap request the tool prints.
4. Docs under `docs/`: no change. None of them states the Step 2 owner rule or the liveness definition; this was checked with grep during planning.

### 5. Verification

1. Run `make ci` from the repo root and read the whole output.
2. Run `claude plugin validate .` and confirm no new warnings.
3. Torch: the pre-commit hook runs `make format`, which exact-syncs this worktree's env. The live shim is baked to `~/git/stockroom`, not this worktree, so no torch restore is needed. Confirm from `grep '^# STOCKROOM_' ~/.local/bin/stockroom` before closing.

## Technology Validation

No new technology - validation not required. The new block uses only constructs the old one used, plus `sed` (POSIX). The prototypes are recorded under Evidence.

## Dependencies

- `/bin/sh` and `sed` on test hosts. `bash` / `zsh` cases skip when absent.
- A non-root test user for the `chmod 000` tests. They skip as root. GitHub-hosted runners run as a non-root user.
- Claude Code's documented cache layout and `${CLAUDE_SKILL_DIR}` substitution.

## Challenges & Mitigations

- **Reversing one first-pass behavior for Claude Code (custom roots were labelled through substitution, verified end to end):** this is scoped to Claude Code by operator decision, with its cost and a ready fallback stated above. Cursor's outcomes are pinned unchanged by `test_cursor_custom_cache_with_env` and the Cursor marketplace and `plugins/local` cases. Preflight should check that no Cursor path gains a question.
- **The `chmod 000` tests can strand tmp dirs or run as root:** the fixture restores the mode in teardown, and the tests skip when `geteuid() == 0`.
- **`_run_block` rework could hide a real regression** if the printed line and the block's variables ever differ. Reading through the printed line is the stricter check, because it is what the agent runs. The red run confirms that the existing cases still read correctly.
- **Fence selection:** `_step2_block` picks the single bash fence that assigns `SKILL_DIR=`. The Step 2 prose must not add a second fence with that assignment.
- **Paths containing `"`, `$` or a backtick** still break Claude Code's raw substitution into `SKILL_DIR="…"`. That limit predates this PR, comes from the substitution rather than the print, and no reviewer raised it. Out of scope, noted for QA.
- **Pre-commit `make format` exact-syncs this worktree's env (removes torch):** harmless here, because no step needs torch and the live shim points elsewhere.

## Pre-Mortem

- **The operator wants Claude Code custom plugins folders to keep auto-labelling too:** the fallback (substitution counts only under `…/plugins/cache/…`) is written into the plan. Switching costs one condition in the block and two test expectations.
- **The empty-`OWNER` prose sends a Cursor agent to the Claude Code branch, or the reverse:** the bullet names the harness explicitly ("In Claude Code" / "In any other harness"), and the agent always knows which harness it runs in. Prose, so it is checked in review, not by a test.
- **"Cannot check" counted as alive strands a contributor whose old checkout sits on a drive that now errors (EIO) rather than vanishing:** the new Step 7 row routes that case to the user with a consented `--takeover --force`. Before this round, the same case crashed `rectify` and left the shim untouched anyway. An unmounted drive gives ENOENT, so it still counts as dead and is replaced, as the operator accepted earlier.
- **A synced copy outside `~/.claude` (custom plugins root) is now `dev`:** Step 7's dev branch stops and asks when `APP_DIR` is not the user's checkout, so this fails safe. No claude.ai-synced stockroom install has been observed.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
