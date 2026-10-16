# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

`sr-initialize` Step 2 reads `$CLAUDE_PLUGIN_ROOT` / `$CURSOR_PLUGIN_ROOT` as shell variables in the agent's shell. Claude Code never puts plugin path variables in the Bash tool's environment, so every Claude Code marketplace install falls through to `OWNER=dev`. Three changes:

- **Step 2:** rewrite it so a marketplace install is recognized by where it lives, and everything else is `dev`, per the operator's rule.
- **`shim rectify`:** make it replace a *dead* shim of any owner, so leaving dev never gets stuck.
- **Step 7:** make it sort an existing shim instead of assuming "live means fine".

Correct the docs and patterns that state the wrong model. Leave both hook files unchanged: the audit found them correct.

### Operator decisions (2026-10-16)

- **Contributors always get `dev`.** A marketplace install must be recognizable as a real install. Anything run from a checkout with intent to develop or iterate is `dev`. That covers `claude --plugin-dir`, Cursor `~/.cursor/plugins/local/`, local-path marketplaces loaded in place, and the Cursor localdev mirror.
- **Hooks stay as they are.** Option B, `rectify` doing nothing on dev loads, is rejected: a dev session's hook must still be able to heal the checkout.
- **`rectify` replaces a dead shim, whoever owns it.** This is approved. It makes the operator's model true: break or remove your dev shim, and the next session of the real install brings it back.
- **No separate dev data (option E rejected).** Dev intentionally runs checkout code against the real warehouse, after a backup.
- **Argument substitution is not a concern.** None of our skills take arguments. No argument test and no hygiene guard; the Step 2 block simply uses no positional tokens.
- **Option A, the install-layout rule, is for `sr-initialize` only.** Hooks are the real-install signal for themselves; `sr-initialize` runs with no hook, so it needs the rule.

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

### Target design

**Step 2 (sr-initialize).** `APP_DIR` always comes from this skill's own directory: `SKILL_DIR/../sr-search`, made absolute with a logical `CDPATH='' cd -- … && pwd`. Then:

1. `APP_DIR` has no `pyproject.toml` → `OWNER=""`, and one stderr line naming `SKILL_DIR`.
2. The plugin root (`${APP_DIR%/*/*}`) is not three levels below a directory named `cache`, as in `<…>/cache/<marketplace>/<plugin>/<version>` → `OWNER=dev`. This is the marketplace-install test, and it applies whatever the plugins root is.
3. It is a real install, and `APP_DIR` matches `*/.claude/plugins/cache/*` → `claude`, or `*/.cursor/plugins/cache/*` → `cursor`.
4. It is a real install elsewhere (for example under `CLAUDE_CODE_PLUGIN_CACHE_DIR`). Then:
   - `${CLAUDE_PLUGIN_ROOT}/skills/sr-search` is physically `APP_DIR` (Claude Code's substitution) → `claude`.
   - Otherwise `${CURSOR_PLUGIN_ROOT}/skills/sr-search` is physically `APP_DIR` → `cursor`.
   - Otherwise `OWNER=""`, and one stderr line saying the harness did not identify itself. The prose tells the agent to set `OWNER` to the harness it is running in.

Block rules:

- No functions, no positional parameters.
- `SKILL_DIR="${CLAUDE_SKILL_DIR}"`, then `[ -n "$SKILL_DIR" ] || SKILL_DIR="<POSIX absolute path of the directory holding this SKILL.md>"`.
- Physical comparisons are precomputed with `CDPATH='' cd -P -- … && pwd`, each guarded by `[ -z "${…_PLUGIN_ROOT}" ] ||`.
- The block ends with `printf "APP_DIR='%s'; OWNER='%s'\n" "$APP_DIR" "$OWNER"`. The prose tells the agent to paste that line as the first statement of every later command, because shell variables do not carry between agent shell calls. If `OWNER` is empty, stop at Step 2.
- Prose never relies on the literal `${CLAUDE_PLUGIN_ROOT}` token being displayed, because Claude Code substitutes it everywhere in the body.

**Step 7 (sr-initialize).** Read the existing shim's header with `grep '^# STOCKROOM_' "$(command -v stockroom)"`. The baked engine is alive when its directory holds `pyproject.toml`. Then:

- **No shim, or same owner as `OWNER`:** harness → `shim install --owner "$OWNER" --app-dir "$APP_DIR"` (bakes the logical path, as the hooks do); `dev` → `make shim` from the repo root.
- **Foreign and dead:** replace it with `--takeover`, as the next session's hook now would anyway. Tell the user what it pointed at.
- **Foreign `dev` shim, alive, baked inside a marketplace install** (`…/cache/<marketplace>/<plugin>/<version>/…`, the old bug's footprint): no harness will ever rebake it. Explain, and offer `--takeover --force` with explicit consent.
- **Foreign and alive otherwise** (another harness's shim, or a contributor's `dev` shim on a checkout): leave it. Say who maintains it. When `OWNER=dev`, point to `make localdev`, which claims the shim for this checkout.

**`shim rectify` (`stockroom.shim`).** When the header parses as a stockroom shim of a different owner and its baked dir is dead (no `pyproject.toml`), write this caller's shim and return `action="rectified"` with a reason naming the replaced owner. A live foreign shim is still a no-op. An unparseable header (not our file, or corrupt) is still a no-op: never overwrite a file we cannot identify. Ensure-env ordering and `--path-only` are unchanged.

**Shim remedy for a missing engine dir.** A new template placeholder for the "baked engine dir … is missing or invalid" line.

- `dev`: "run 'make shim' from a stockroom checkout, or start a new session of a harness with the stockroom plugin installed".
- Harness owners: keep `_HARNESS_REMEDY`.
- The "engine env not ready" line keeps `{{REMEDY}}`, because a new session cannot fix a live dev engine's env.

## Test Plan (TDD)

### Behaviors to Verify

**Step 2 block** (`test_initialize_context.py`). The fence is extracted from `skills/sr-initialize/SKILL.md` and run with a controlled env (`PATH`, `HOME`, plus per-case variables only), once per shell: `sh`, plus `bash` and `zsh` when installed, skipped when absent. The test reads back `OWNER` and `APP_DIR`.

- "Claude rendering" replaces the exact tokens `${CLAUDE_PLUGIN_ROOT}` (plugin skills only) and `${CLAUDE_SKILL_DIR}`.
- "Agent fill" replaces the angle-bracket placeholder with the skill dir.
- Fixture installs are built under `tmp_path` with `skills/sr-initialize/` and `skills/sr-search/pyproject.toml`.

Cases:

1. **Claude marketplace**: `home/.claude/plugins/cache/m/stockroom/2.1.1`, Claude plugin rendering → `claude`, `APP_DIR=<root>/skills/sr-search`. Red today.
2. **Claude marketplace without substitution** (agent fill) → `claude`. Red today.
3. **Claude custom plugins root**: `pc/cache/m/stockroom/2.1.1`, rendering → `claude`, through substitution only. Red today.
4. **Claude `--plugin-dir` checkout** (with `Makefile` and `.git`), rendering → `dev`.
5. **Claude local-path marketplace in place**: root `src/market/plugins/stockroom`, rendering → `dev`.
6. **Cursor marketplace**: `home/.cursor/plugins/cache/m/stockroom/<sha>`, agent fill, no env → `cursor`. Red today.
7. **Cursor custom cache** `x/cache/m/stockroom/<sha>`, agent fill, env `CURSOR_PLUGIN_ROOT=<root>` → `cursor`.
8. **Cursor `plugins/local`**: `home/.cursor/plugins/local/stockroom`, agent fill, env `CURSOR_PLUGIN_ROOT=<root>` → `dev`. Red today.
9. **Cursor localdev mirror**: `<repo>/.cursor/skills/stockroom-local/{sr-initialize,sr-search}` symlinks, agent fill → `dev`, `APP_DIR == <repo>/.cursor/skills/stockroom-local/sr-search`, `realpath(APP_DIR) == <repo>/skills/sr-search`.
10. **Leaked root**: case 3, plus env `CURSOR_PLUGIN_ROOT` pointing at a different cache-shaped plugin with its own `skills/sr-search` → `claude`. Red today.
11. **Unattributable real install**: `x/cache/m/stockroom/v`, agent fill, no env → `OWNER` empty. Red today.
12. **Wrong skill dir** → `OWNER` and `APP_DIR` empty. Red today.
13. **Unfilled placeholder** (verbatim, no env) → `OWNER` empty.

**`rectify` policy** (`test_shim.py::TestRectify`):

- Dead foreign shim (another owner, baked dir without `pyproject.toml`) → rewritten for the caller; `action == "rectified"`; file equals `render(caller_app_dir, caller_owner)`. Red today.
- The same with `ensure_env=False`, the path-only hook → also replaced. Red today.
- Live foreign shim → untouched, `noop`. This is the existing `test_owner_mismatch_never_touches_foreign_shim`, with its docstring narrowed to "live".
- Unparseable header (a non-stockroom file at dest) → untouched, `noop`. Green today; it guards the new branch.

**Shim runtime** (`test_shim_runtime.py`): the existing missing-dir and env-not-ready parametrizations keep their remedy tokens ("make shim" for `dev`, "sr-initialize" for harnesses). They cover the new placeholder plumbing, because an unsubstituted placeholder fails them. No new wording oracle.

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`
- Conventions: a module docstring stating the contract, per-test docstrings, the `repo_root` fixture, and `subprocess.run` with an explicit minimal env (as in `test_shim_runtime.py`). `TestRectify` stubs `ensure_engine_env`. The `engine_dir` / `other_engine_dir` fixtures are alive; a dead dir is a path without `pyproject.toml`.
- New test files: `skills/sr-search/tests/test_initialize_context.py`

## Implementation Plan

### 1. `shim rectify` replaces a dead shim of any owner — executable

- Files: `skills/sr-search/tests/test_shim.py`, `skills/sr-search/src/stockroom/shim.py`

1. Stub tests: add documented empty `TestRectify` cases: `test_foreign_owner_dead_dir_is_replaced`, `test_path_only_replaces_dead_foreign`, `test_unparseable_dest_left_untouched`. Narrow `test_owner_mismatch_never_touches_foreign_shim`'s docstring to a live foreign shim.
2. Stub interface: none (same `rectify` signature).
3. Write tests and run red: build the dead foreign shim by installing for owner `dev` at a dir, then deleting that dir's `pyproject.toml`. Run `pytest tests/test_shim.py -n0`; the two replacement cases fail.
4. Write code and run green:
   - In `rectify`, after the absent-dest branch: header `None` → noop ("unidentified file"); foreign owner and `_alive(header["app_dir"])` → noop ("live foreign owner"); foreign and dead → `_write_atomic(dest, render(app_dir, owner))`, then `ShimReport(action="rectified", reason=f"replaced dead '{header['owner']}' shim")`.
   - Update the `rectify` docstring and the module docstring ("never touches a foreign owner" becomes "never touches a live foreign owner or an unidentified file").
   - Re-run until green.

### 2. Shim remedy for a missing engine dir — prose/policy

- Files: `skills/sr-search/src/stockroom/shim.py`, `skills/sr-search/src/stockroom/shim_template.sh`
- No tests: prose/policy artifact. The existing runtime remedy-token tests already guard the placeholder plumbing.

1. Add `_DEV_GONE_REMEDY` and a `{{GONE_REMEDY}}` placeholder on the template's missing-dir line. `render` substitutes the dev text for `dev` and `_HARNESS_REMEDY` otherwise. Keep it free of shell-active characters.
2. Run `pytest tests/test_shim.py tests/test_shim_runtime.py -n0` to confirm the existing tokens still pass.

### 3. sr-initialize Step 2 context resolution — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests: the module docstring states the harness-rendering model and the operator's rule (marketplace cache install = real, all else `dev`). Add helper stubs `_step2_block(repo_root)` (the single ```` ```bash ```` fence assigning `SKILL_DIR=`), `_render_claude(block, *, plugin_root, skill_dir)`, `_fill_placeholder(block, skill_dir)`, `_run_block(shell, block, env)`, and `_plugin_tree(root)`. Add a `shell` fixture parametrized over `sh`/`bash`/`zsh` that skips absent shells, and one empty, documented test per case 1–13.
2. Stub interface: none. The "interface" is the Step 2 fence, and the tests run against the current block first.
3. Write tests and run red:
   - `_run_block` runs `[shell, "-c", block + '\nprintf "%s\\n%s\\n" "$OWNER" "$APP_DIR"']` with `env={"PATH": os.environ["PATH"], "HOME": tmp_home, **case_env}` and takes the last two stdout lines.
   - Run `pytest tests/test_initialize_context.py -n0` and confirm the cases marked "Red today" fail.
4. Write code and run green:
   - Rewrite the Step 2 block and its prose to the target design.
   - Replace "Neither env var set means you are in a dev checkout" with what each outcome means. Contributor flows: `make localdev` / `make shim`.
   - Re-run until green under every installed shell.

### 4. sr-initialize Step 7 triage and the idempotency paragraph — prose/policy

- Files: `skills/sr-initialize/SKILL.md`
- No tests: prose/policy artifact

1. Rewrite Step 7 to the target triage, keeping the refusal, PATH-warning and success relay bullets. Add `--app-dir "$APP_DIR"` to the install command.
2. Update the "Idempotent by design" paragraph: "shim present and owned → nothing to do" becomes "shim live and maintained by its owner → nothing to do".

### 5. Docs and shared patterns — prose/policy

- Files:
  - `docs/contributing/preparation.md`
  - `docs/user-guide/troubleshooting/index.md`
  - `docs/architecture/packaging.md`
  - `memory-bank/systemPatterns.md`
- No tests: prose/policy artifact

1. `preparation.md`:
   - "Changing the Hooks": the plugin-root variables exist only in hook processes of a plugin the harness has loaded (a marketplace install, `--plugin-dir`, or Cursor `plugins/local`), never in project hooks or agent shells.
   - "Done Developing" and "Clean Semantics": a dead `dev` shim (the checkout was deleted) is now replaced at the next session of an installed stockroom plugin; `make localdev-clean` remains the tidy exit.
2. `troubleshooting/index.md`:
   - "Ownership" note: a live foreign shim needs `--takeover --force`; a dead one needs `--takeover`, and the next harness session now replaces a dead shim on its own.
   - "Shim refuses" section: mention that a new session heals a dead shim.
3. `packaging.md` rectify row: "never touch a foreign owner" becomes "replace a dead shim of any owner; never touch a live foreign one".
4. `systemPatterns.md`:
   - In the "Baked-only" paragraph, rectify also replaces a dead shim of any owner.
   - In "Dual-manifest plugin", add one sentence: plugin-root variables reach hook processes only; skills find the engine as their sibling directory; Claude Code supplies paths only through exact `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` substitution; a real install is a marketplace cache copy (`…/cache/<marketplace>/<plugin>/<version>`).

### 6. Verification and memory

1. Run `make ci`, or the format, lint, test and reuse gates, and read the whole output.
2. Torch: confirm from the shim header that the live shim is not baked to this worktree. If it is, run `stockroom shim ensure-env`.
3. Run `claude plugin validate .` and confirm no new warnings.
4. Run `.summem/summem note` with the repo facts: the sr-initialize owner rule; rectify replaces dead shims; marketplace installs contain `.git` and `Makefile`.

## Technology Validation

No new technology. Claude Code's skill-text substitution was checked with a headless probe on 2.1.301; results are above.

## Dependencies

- `/bin/sh` on test hosts (CI runs Linux). `bash` / `zsh` cases skip when the shell is absent.
- Claude Code's documented cache layout and skill substitution.

## Challenges & Mitigations

- **Cursor's cache layout is observed, not documented.** It matches Claude's documented shape on this machine. A Cursor real install in some other layout with no `CURSOR_PLUGIN_ROOT` gets `dev` from rule 2. The skill's dev branch says to run `make localdev` / `make shim` from a repo root, which visibly won't apply; QA should note any real counterexample.
- **Dead-shim takeover and briefly unavailable drives:** a `dev` shim baked on an unmounted volume looks dead and is replaced at the next session. Accepted by the operator. The fix is `make local-engine` again.
- **Never overwrite unknown files:** an unparseable header stays a no-op in `rectify`.
- **A test that parses `SKILL.md` could drift into a change-detector.** Select the fence by its `SKILL_DIR=` assignment and assert only resolved outputs.
- **Tests run inside harness sessions:** pass an explicit minimal `env`.
- **zsh is absent here and on CI.** The block uses only `printf`, `[ … = … ]`, `case`, `$(…)` and `${…%…}` parameter expansion, all valid in zsh. macOS zsh stays untested by CI, a residual risk noted for QA.
- **Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` everywhere in the body:** keep the literal token out of prose.

## Pre-Mortem

- **The layout rule misjudges a real install** (a harness changes its cache layout). The rule matches the layout Claude Code documents for `${CLAUDE_PLUGIN_ROOT}` and Cursor's observed copy. A mismatch gives `dev`, and Step 7's dev branch visibly does not apply. That is a visible failure, not a silent mislabel.
- **Dead-shim takeover fights a contributor:** it only fires on a dead baked dir, and a live checkout is never touched. Two real installs (Claude and Cursor) can swap ownership only when one's engine dir is gone, which is benign.
- **"Fix the hooks" was the wrong layer:** the operator agreed. Hooks are unchanged, and dev sessions still self-heal the checkout.
- **Existing victims** (a `dev` shim baked inside a cache, still alive) are recognized by Step 7 and offered a consented takeover. Once the old cache is cleaned up, `rectify` replaces them automatically.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
