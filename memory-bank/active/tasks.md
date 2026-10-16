# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

`sr-initialize` Step 2 reads `$CLAUDE_PLUGIN_ROOT` / `$CURSOR_PLUGIN_ROOT` as shell variables in the agent's shell. Claude Code never puts plugin path variables in the Bash tool's environment, so every Claude Code marketplace install falls through to `OWNER=dev`. Cursor documents no agent-shell plugin root either. Rewrite Step 2 so it always finds the engine as this skill's sibling, and picks the owner from mechanisms that exist:

- Claude Code's inline skill-text substitution of the exact tokens `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}`
- a `CURSOR_PLUGIN_ROOT` that Cursor may export
- the install path: a harness `plugins/` tree, otherwise dev

Each plugin root counts only when its engine is this skill's engine. Then make Step 7 sort an existing shim by its header: leave maintained shims alone, and offer a consented takeover only for a shim nobody maintains. Correct the doc sentences and the system pattern that state the wrong model. Leave both hook files unchanged: the audit found them correct.

### Evidence that shaped the plan

- **Claude Code docs** ([plugins reference, Environment variables](https://code.claude.com/docs/en/plugins-reference#environment-variables); [skills, string substitutions](https://code.claude.com/docs/en/skills#available-string-substitutions)): plugin path variables resolve inline in hook `command` and are exported to hook, MCP stdio and LSP processes. They "aren't present in the environment of commands Claude runs through the Bash tool". In skill content, write `${...}` and Claude Code substitutes it at load.
- **Probe on Claude Code 2.1.301**, run headless (`claude -p`) with a throwaway plugin and a project skill:
  - In plugin skills, `${CLAUDE_PLUGIN_ROOT}` is substituted, including inside quotes and code fences.
  - Bare `$CLAUDE_PLUGIN_ROOT`, `${CLAUDE_PLUGIN_ROOT:-x}` and `${CURSOR_PLUGIN_ROOT}` stay literal.
  - In project skills, `${CLAUDE_PLUGIN_ROOT}` stays literal and `${CLAUDE_SKILL_DIR}` is substituted. Neither has a trailing slash.
- **Bash tool on 2.1.301**: no `*_PLUGIN_ROOT` in the environment. The warehouse shows the same in July 2026 (plugin 0.1.1); that agent quietly improvised `OWNER=claude`.
- **Cursor**:
  - Docs cover `${CURSOR_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_ROOT}` expansion only in MCP config.
  - Staff on the forum endorse `${CURSOR_PLUGIN_ROOT}` in `hooks.json` ([thread](https://forum.cursor.com/t/inconsistent-working-directory-for-plugin-hook-commands/153236)), and hook processes receive both variables ([CLI leak report](https://forum.cursor.com/t/cursor-cli-2026-08-04-leaks-claude-plugin-root-between-concurrent-plugin-hooks/167628); nested children may see another plugin's root).
  - Nothing documents the variables in agent shells or substitution in skill text. In the warehouse (April 2026), Cursor inlined a command body with `${CURSOR_PLUGIN_ROOT}` still literal.
- **Install dirs**: both `~/.claude/plugins/cache/.../stockroom/<ver>/` and `~/.cursor/plugins/cache/.../stockroom/<sha>/` contain `.git` **and** `Makefile`. So "checkout markers → dev", the bug report's option 3, would misfire on marketplace installs. It also means an agent that followed today's "defer to `make shim` from the repo root" inside a plugin cache succeeds, leaving a `dev`-owned shim baked to the cache that no hook will ever rebake.
- **Localdev layouts**: the Cursor mirror is `<repo>/.cursor/skills/stockroom-local/<skill>`, made of symlinks to `../../../skills/<skill>`. Claude localdev is `claude --plugin-dir <repo>`, and that session's own SessionStart hook runs `shim rectify --owner claude --app-dir <repo>/skills/sr-search`.
- **Hooks audit**: `hooks/claude-hooks.json` uses `${CLAUDE_PLUGIN_ROOT}` inside double quotes in a hook `command`, which is documented to resolve. `claude plugin validate .` passes with no hook warnings. `hooks/cursor-hooks.json` uses `${CURSOR_PLUGIN_ROOT}`, which staff endorse. Both expand the root in the hook's own shell and pass it to the engine as `--app-dir`. No Python code reads the variable, so the leak into nested children cannot misroute. Result: no hook change.
- **Shim policy** (`stockroom.shim`): `rectify` never touches a foreign owner. `install` refuses a foreign owner unless `--takeover` is passed (baked dir dead, meaning no `pyproject.toml`) or `--takeover --force` (baked dir alive). The header carries `# STOCKROOM_OWNER=` and `# STOCKROOM_APP_DIR=`.

### Target Step 2 resolution (design)

`APP_DIR` always comes from this skill's own directory: `SKILL_DIR/../sr-search`, made absolute with a logical `CDPATH='' cd -- … && pwd`, which keeps symlinked homes and mirror paths as the harness sees them. A plugin root counts only when `<root>/skills/sr-search` is physically the same directory as `APP_DIR`. That guards against inherited or leaked variables (advisory A1). `OWNER` is chosen in this order:

1. `APP_DIR` has no `pyproject.toml` → no owner (`OWNER=` empty), and one stderr line naming `SKILL_DIR`.
2. `${CURSOR_PLUGIN_ROOT}` holds this engine (through Cursor's env, or any future substitution) → `cursor`.
3. `${CLAUDE_PLUGIN_ROOT}` holds this engine (through Claude Code's substitution in plugin skills) → `claude`.
4. `APP_DIR` is under `*/.cursor/plugins/*` → `cursor`; under `*/.claude/plugins/*` → `claude`. This covers Cursor without an agent-shell variable, and Claude without substitution.
5. Otherwise → `dev`: a localdev mirror, or a checkout used as plain skills. Step 7 defers to `make shim`.

Block shape:

- `SKILL_DIR="${CLAUDE_SKILL_DIR}"`, then `[ -n "$SKILL_DIR" ] || SKILL_DIR="<POSIX absolute path of the directory holding this SKILL.md>"`. On WSL, Cursor shows backslash paths, so the placeholder asks for POSIX (A5).
- A `holds_engine` helper does the same-directory check with `cd -P`.
- The block ends with `printf '%s\n' "OWNER=$OWNER APP_DIR=$APP_DIR"`, using `printf` rather than `echo`, so zsh does not interpret backslashes.
- The prose tells the agent to set those printed values again at the start of every later command, because shell variables do not carry between agent shell calls (A3). If `OWNER` is empty, stop at Step 2.

**Decision, A2 (recorded for the operator):** `claude --plugin-dir <checkout>` resolves to `claude`, not `dev`. In that same session, the SessionStart hook already creates a `claude`-owned shim at the checkout when none exists, so Step 2 agrees with the hook instead of fighting it. Contributor `dev` shims still come from `make shim` / `make local-engine`, and Step 7 leaves a live `dev` shim on a checkout alone. Brief UC3 and AC3 are updated to match.

**Declined, radical idea (an engine `shim context` resolver):** the defect is the skill text's contract with harness substitution, and only a test that runs the shipped block catches a regression to an unbraced or unsubstituted token. A Python resolver would still need that block test, so it adds a CLI surface without removing one. Two parts of the idea are logged as follow-up candidates for the reflection: `doctor probe` reporting a mis-owned shim, and `shim install --owner dev` warning when it bakes inside a harness plugins tree.

## Test Plan (TDD)

### Behaviors to Verify

The Step 2 fenced block is extracted from `skills/sr-initialize/SKILL.md` and run with a controlled env (`PATH`, `HOME`, plus per-case variables only), once per shell: `sh`, plus `bash` and `zsh` when installed, skipped when absent (A4). The test then reads back `OWNER` and `APP_DIR`. "Claude rendering" replaces the exact tokens `${CLAUDE_PLUGIN_ROOT}` (plugin skills only) and `${CLAUDE_SKILL_DIR}` with paths, as the probe verified. "Agent fill" replaces the angle-bracket placeholder with the skill directory, as a Cursor agent does.

- **Claude plugin, custom config dir**: plugin root at `tmp/cfg/plugins/cache/m/stockroom/2.1.1` (not under `.claude/plugins`), Claude plugin rendering, empty env → `OWNER=claude`, `APP_DIR=<root>/skills/sr-search`. Red today; passes only if the substitution is used.
- **Claude `--plugin-dir` checkout**: root is a checkout with `Makefile` and `.git`, Claude plugin rendering → `OWNER=claude`, `APP_DIR=<checkout>/skills/sr-search`. Red today.
- **Claude cache, no substitution** (older Claude, agent fill): engine under `tmp/home/.claude/plugins/cache/...` → `OWNER=claude` by the path rule. Red today.
- **Cursor with `CURSOR_PLUGIN_ROOT` exported**: plugin root outside any `.cursor/plugins` tree, agent fill, env `CURSOR_PLUGIN_ROOT=<root>` → `OWNER=cursor`. Passes only through the env check.
- **Cursor marketplace, no agent-shell variable**: engine under `tmp/home/.cursor/plugins/cache/m/stockroom/<sha>`, agent fill, empty env → `OWNER=cursor`. Red today.
- **Cursor localdev mirror**: `<repo>/.cursor/skills/stockroom-local/{sr-initialize,sr-search}` symlinks into a checkout, agent fill, empty env → `OWNER=dev`, `APP_DIR == <repo>/.cursor/skills/stockroom-local/sr-search` (the logical mirror path), and `realpath(APP_DIR) == <repo>/skills/sr-search`.
- **Leaked plugin root (A1)**: Claude plugin rendering for a custom-config-dir root, plus env `CURSOR_PLUGIN_ROOT` pointing at a different plugin tree that has its own `skills/sr-search` → `OWNER=claude`, not `cursor`. Red today.
- **Edge, wrong skill dir**: agent fill with a directory that has no sibling `sr-search` → `OWNER` empty, `APP_DIR` empty. Red today, where the result is `dev`.
- **Edge, unfilled placeholder** (block run verbatim outside Claude Code, no env) → `OWNER` empty.

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`
- Conventions: `test_<area>.py`, a module docstring stating the contract, per-test docstrings, the `repo_root` fixture from `conftest.py`, and a `subprocess.run` with an explicit minimal env and `tmp_path` fixture trees (as in `test_shim_runtime.py`).
- New test files: `skills/sr-search/tests/test_initialize_context.py`

## Implementation Plan

### 1. sr-initialize Step 2 context resolution — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests: create `test_initialize_context.py` with a module docstring covering:
   - the harness-rendering model (Claude exact-token substitution, agent placeholder fill)
   - helper stubs `_step2_block(repo_root)`, `_render_claude(block, *, plugin_root, skill_dir)`, `_fill_placeholder(block, skill_dir)`, `_run_block(shell, block, env)`, and a `_plugin_tree(root)` builder (`skills/sr-initialize/`, plus `skills/sr-search/pyproject.toml`)
   - a `shell` fixture parametrized over `sh`/`bash`/`zsh` that skips absent shells
   - one empty, documented test per behavior above
2. Stub interface: none. The "interface" is the Step 2 fenced block in `SKILL.md`, and the tests run against the current block first.
3. Write tests and run red: implement the helpers.
   - `_step2_block` returns the single ```` ```bash ```` fence in `SKILL.md` that assigns both `OWNER=` and `APP_DIR=`, asserting there is exactly one.
   - `_fill_placeholder` replaces each `<…>` placeholder inside the block.
   - `_run_block` runs `[shell, "-c", block + '\nprintf "%s\\n%s\\n" "$OWNER" "$APP_DIR"']` with `env={"PATH": os.environ["PATH"], "HOME": tmp_home, **case_env}`, takes the last two stdout lines, and returns them.
   - Implement every case.
   - Run `uv --directory skills/sr-search --no-config run --no-sync pytest tests/test_initialize_context.py -n0` and confirm the cases flagged "Red today" fail against the current block.
4. Write code and run green: rewrite the Step 2 block and its surrounding prose in `skills/sr-initialize/SKILL.md` to the target design.
   - Use `CDPATH='' cd --` and the `holds_engine` same-directory check.
   - End the block with the `printf` line.
   - Add the prose for re-setting variables and for stopping on an empty owner.
   - Write prose that does not depend on the literal token being displayed, since Claude Code substitutes the token everywhere in the body.
   - Replace "Neither env var set means you are in a dev checkout" with the real meaning of each outcome.
   - Re-run the file until green under every installed shell.

### 2. sr-initialize Step 7 shim triage, and the idempotency paragraph — prose/policy

- Files: `skills/sr-initialize/SKILL.md`
- No tests: prose/policy artifact

1. Rewrite Step 7 to read the existing shim first: `grep '^# STOCKROOM_' "$(command -v stockroom)"` gives the incumbent owner and baked `APP_DIR`. The baked engine is alive when that directory holds `pyproject.toml`, the shim's own test. Then:
   - **No shim on PATH, or same owner as `OWNER`:** harness owner → `shim install --owner "$OWNER"`, a create or same-owner rewrite; `dev` → `make shim` from the repo root.
   - **Foreign owner, baked engine dead:** the install refuses with `--takeover` in the message. Offer `--takeover` with the user's explicit consent.
   - **Foreign `dev` owner, alive, baked inside `*/.claude/plugins/*` or `*/.cursor/plugins/*`:** nobody maintains it. No harness hook rebakes a `dev` shim, and the plugin update will remove that directory. Explain this and offer `--takeover --force` with explicit consent.
   - **Otherwise foreign and alive** (another harness's shim kept by its own hooks, or a contributor's `dev` shim on a checkout): nothing to do. Tell the user which owner maintains it, and that `stockroom` works.
   - **Empty `OWNER`:** go back to Step 2.
   - Keep the refusal, PATH-warning and success relay bullets.
2. Update the "Idempotent by design" paragraph (SKILL.md line 11): "shim present and owned → nothing to do" becomes "shim live and maintained by its owner → nothing to do".

### 3. Docs and shared patterns — prose/policy

- Files: `docs/contributing/preparation.md`, `docs/user-guide/troubleshooting/index.md`, `memory-bank/systemPatterns.md`
- No tests: prose/policy artifact

1. `docs/contributing/preparation.md` "Changing the Hooks": say the plugin-root variables exist only in hook processes of a plugin the harness has loaded (a marketplace install, or `claude --plugin-dir`), never in project hooks or agent shells. Copying `hooks/*.json` into a project therefore cannot work.
2. `docs/user-guide/troubleshooting/index.md` "Ownership" note (line 70): a live foreign shim needs `--takeover --force`; a dead one needs `--takeover`. Point to `sr-initialize` for the consented path. Check that the line 117 and line 125 statements ("hooks can see …", "that skill can see the plugin tree") stay accurate; they should need no change.
3. `memory-bank/systemPatterns.md` "Dual-manifest plugin": add one sentence.
   - Plugin-root variables reach harness hook processes only, never agent-run shell commands.
   - A skill finds the engine as its sibling `../sr-search`. Claude Code supplies paths only through exact `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` substitution in skill text.
   - Wrapper skills still carry no paths.

### 4. Verification and memory

1. Run `make ci`, or the format, lint, test and reuse gates it chains, and read the whole output.
2. Torch (A7): `make sync` strips torch only from this worktree's engine `.venv`. Confirm from the shim header that the live shim is not baked to this worktree. If it is, run `stockroom shim ensure-env` afterwards.
3. Run `claude plugin validate .` and confirm no new warnings.
4. Run `.summem/summem note` with one repo fact: sr-initialize resolves the engine as its sibling and the owner via a verified Claude substitution, Cursor env, the plugins-path rule, or dev; marketplace installs contain `.git` and `Makefile`.

## Technology Validation

No new technology. The one external behavior the design rests on, Claude Code's skill-text substitution, was checked with a headless probe on 2.1.301; results are recorded above.

## Dependencies

- `/bin/sh` on test hosts (CI runs Linux). `bash` / `zsh` cases skip when the shell is absent.
- Claude Code's documented skill substitution. The probe fixed the exact-token semantics the test models.

## Challenges & Mitigations

- **Cursor agent-shell behavior is undocumented.** Step 2 does not depend on it: the env check catches an exported variable, and the `.cursor/plugins` path rule catches everything else. Optional UAT for the operator in Cursor: ask the agent to run `echo "[${CURSOR_PLUGIN_ROOT-unset}]"`, then run `/sr-initialize` and read the Step 2 line it prints.
- **Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` everywhere in the body, prose included.** Keep the literal token out of prose that must read correctly in both harnesses; name it in code only.
- **A test that parses `SKILL.md` could drift into a change-detector.** Select the block by behavior (the one fence that assigns `OWNER=` and `APP_DIR=`) and assert only resolved outputs, never wording.
- **Tests run inside harness sessions** (`CLAUDECODE`, maybe `CURSOR_PLUGIN_ROOT` inherited). Pass an explicit minimal `env` to `subprocess.run`.
- **Symlinked homes** (dotfile managers linking `~/.claude`): use logical `pwd` for `APP_DIR` and the path rule, as the hooks' logical `${…}/skills/sr-search` does, so the shim bake matches the hook bake. The same-directory guard compares physical paths, so a logical/physical mismatch between a root and `APP_DIR` does not reject a true match.
- **zsh quirks** (the Bash tool may run zsh): only `printf`, `[ … = … ]`, `case`, and a function declared with `name() { …; }`. All shells that are present run the block in the tests.

## Pre-Mortem

- **The premise is wrong for Cursor** (for example, Cursor substitutes `${CLAUDE_PLUGIN_ROOT}` in skills for Claude compatibility). The Cursor check comes first and uses the braced token, which any such substitution would also fill. The Cursor path rule precedes dev. The UAT line is recorded for the operator.
- **The fix lands, but existing victims keep a mis-owned shim.** Step 7's triage recognizes a `dev` shim baked inside a harness plugins tree and offers a consented takeover. Healthy shims are left alone, which was preflight finding 2.
- **"Fix the hooks" was the wrong layer.** The audit shows the hooks are already correct; changing them would add risk with no benefit. Scope keeps hooks unchanged and records why.
- **The "dev" label is still wrong for some real install layout** (a custom Cursor plugin dir outside `~/.cursor/plugins`, with no Cursor env var). Such layouts are not documented install paths. Step 7's dev branch tells the agent to run `make shim` from the repo root, which visibly does not apply there. Record a real counterexample in the reflection if QA finds one.
- **The contributor owner changes under `--plugin-dir`.** Accepted, and recorded as decision A2 for the operator. It matches the session's own hook. Step 7 does not disturb a contributor's live `dev` shim.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
