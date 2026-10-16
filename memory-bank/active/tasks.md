# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

`sr-initialize` Step 2 reads `$CLAUDE_PLUGIN_ROOT` / `$CURSOR_PLUGIN_ROOT` as shell variables in the agent's shell. Claude Code never puts plugin path variables in the Bash tool's environment, so every Claude Code marketplace install falls through to `OWNER=dev`. Cursor documents no agent-shell plugin root either. Rewrite Step 2 so it always finds the engine as this skill's sibling, and picks the owner from mechanisms that exist:

- Claude Code's inline skill-text substitution of the exact tokens `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_SKILL_DIR}`
- a `CURSOR_PLUGIN_ROOT` that Cursor may export
- the install path: a harness `plugins/` tree, otherwise dev

Fix Step 7 so a re-run repairs a shim that a harness's hooks will never refresh. Correct the one contributor-doc sentence and the system pattern that state the wrong model. Leave both hook files unchanged: the audit found them correct.

### Evidence that shaped the plan

- **Claude Code docs** ([plugins reference, Environment variables](https://code.claude.com/docs/en/plugins-reference#environment-variables); [skills, string substitutions](https://code.claude.com/docs/en/skills#available-string-substitutions)): plugin path variables resolve inline in hook `command` and are exported to hook, MCP stdio and LSP processes. They "aren't present in the environment of commands Claude runs through the Bash tool". In skill content, write `${...}` and Claude Code substitutes it at load.
- **Probe on Claude Code 2.1.301**, run headless (`claude -p`) with a throwaway plugin and a project skill:
  - In plugin skills, `${CLAUDE_PLUGIN_ROOT}` is substituted, including inside quotes and code fences.
  - Bare `$CLAUDE_PLUGIN_ROOT`, `${CLAUDE_PLUGIN_ROOT:-x}` and `${CURSOR_PLUGIN_ROOT}` stay literal.
  - In project skills, `${CLAUDE_PLUGIN_ROOT}` stays literal and `${CLAUDE_SKILL_DIR}` is substituted. Neither has a trailing slash.
- **Bash tool on 2.1.301**: no `*_PLUGIN_ROOT` in the environment. The warehouse shows the same in July 2026 (plugin 0.1.1); that agent quietly improvised `OWNER=claude`.
- **Cursor**:
  - Docs cover `${CURSOR_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_ROOT}` expansion only in MCP config.
  - Staff on the forum endorse `${CURSOR_PLUGIN_ROOT}` in `hooks.json` ([thread](https://forum.cursor.com/t/inconsistent-working-directory-for-plugin-hook-commands/153236)), and hook processes receive both variables ([CLI leak report](https://forum.cursor.com/t/cursor-cli-2026-08-04-leaks-claude-plugin-root-between-concurrent-plugin-hooks/167628)).
  - Nothing documents the variables in agent shells or substitution in skill text. In the warehouse (April 2026), Cursor inlined a command body with `${CURSOR_PLUGIN_ROOT}` still literal.
- **Install dirs**: both `~/.claude/plugins/cache/.../stockroom/<ver>/` and `~/.cursor/plugins/cache/.../stockroom/<sha>/` contain `.git` **and** `Makefile`. So "checkout markers → dev", the bug report's option 3, would misfire on marketplace installs. The Cursor localdev mirror is `<repo>/.cursor/skills/stockroom-local/<skill>`, made of symlinks to `../../../skills/<skill>`. Claude localdev is `claude --plugin-dir <repo>`.
- **Hooks audit**: `hooks/claude-hooks.json` uses `${CLAUDE_PLUGIN_ROOT}` inside double quotes in a hook `command`, which is documented to resolve. `claude plugin validate .` passes with no hook warnings. `hooks/cursor-hooks.json` uses `${CURSOR_PLUGIN_ROOT}`, which staff endorse. Both pass the root to the engine as `--app-dir`, and no Python code reads the variable, so the reported CLI env leak into nested children cannot misroute. Result: no hook change.
- **Shim policy** (`stockroom.shim`): `rectify` never touches a foreign owner. A `dev`-labelled shim baked to a plugin cache is therefore never refreshed by that harness's hooks. Today's Step 7 says "already live → nothing to do", so a re-run cannot repair it.

### Target Step 2 resolution (design)

`APP_DIR` always comes from this skill's own directory: `SKILL_DIR/../sr-search`, made absolute with logical `cd … && pwd`, as the shim's `_absolute` does. The plugin-root variables only choose `OWNER`, in this order:

1. `APP_DIR` has no `pyproject.toml` → no owner (`OWNER=` empty), with a one-line message to fix `SKILL_DIR`.
2. `${CURSOR_PLUGIN_ROOT}` is non-empty, through Cursor's env or any future substitution → `cursor`.
3. `${CLAUDE_PLUGIN_ROOT}` is non-empty, through Claude Code's substitution in plugin skills → `claude`.
4. `APP_DIR` is under `*/.cursor/plugins/*` → `cursor`; under `*/.claude/plugins/*` → `claude`. This covers Cursor without an agent-shell variable, and Claude without substitution.
5. Otherwise → `dev`: a localdev mirror or checkout. Step 7 defers to `make shim`.

`SKILL_DIR="${CLAUDE_SKILL_DIR}"` is followed by an agent-filled placeholder fallback for other harnesses. Cursor gives the agent the `SKILL.md` path (with backslashes on WSL). `claude --plugin-dir <checkout>` resolves to `claude`. That matches the SessionStart hook the same session runs, and the contributor `make shim` / `make local-engine` flows are unchanged.

## Test Plan (TDD)

### Behaviors to Verify

The Step 2 fenced block is extracted from `skills/sr-initialize/SKILL.md` and run under `/bin/sh` with a controlled env (`PATH`, `HOME`, plus per-case variables only). The test then reads back `OWNER` and `APP_DIR`. "Claude rendering" replaces the exact tokens `${CLAUDE_PLUGIN_ROOT}` (plugin skills only) and `${CLAUDE_SKILL_DIR}` with paths, as the probe verified. "Agent fill" replaces the angle-bracket placeholder with the skill directory, as a Cursor agent does.

- **Claude plugin, custom config dir**: plugin root at `tmp/cfg/plugins/cache/m/stockroom/2.1.1` (not under `.claude/plugins`), Claude plugin rendering, empty env → `OWNER=claude`, `APP_DIR=<root>/skills/sr-search`. Red today; passes only if the substitution is used.
- **Claude `--plugin-dir` checkout**: root is a checkout with `Makefile` and `.git`, Claude plugin rendering → `OWNER=claude`.
- **Claude cache, no substitution** (older Claude, agent fill): engine under `tmp/home/.claude/plugins/cache/...` → `OWNER=claude` by the path rule.
- **Claude project skill in a checkout** (only `${CLAUDE_SKILL_DIR}` rendered) → `OWNER=dev`.
- **Cursor with `CURSOR_PLUGIN_ROOT` exported**: plugin root outside any `.cursor/plugins` tree, agent fill → `OWNER=cursor`. Passes only through the env check.
- **Cursor marketplace, no agent-shell variable**: engine under `tmp/home/.cursor/plugins/cache/m/stockroom/<sha>`, agent fill, empty env → `OWNER=cursor`. Red today.
- **Cursor localdev mirror**: `<repo>/.cursor/skills/stockroom-local/{sr-initialize,sr-search}` symlinks into a checkout, agent fill, empty env → `OWNER=dev`, and `APP_DIR` resolves to `<repo>/skills/sr-search`.
- **Edge, wrong skill dir**: `SKILL_DIR` points where no sibling engine exists → `OWNER` empty, so no owner is chosen. Red today, where the result is `dev`.
- **Edge, unfilled placeholder** (agent runs the block verbatim outside Claude Code) → `OWNER` empty.

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`
- Conventions: `test_<area>.py`, a module docstring stating the contract, per-test docstrings, the `repo_root` fixture from `conftest.py`, and a `subprocess.run` of `sh` with an explicit minimal env and `tmp_path` fixture trees (as in `test_shim_runtime.py`).
- New test files: `skills/sr-search/tests/test_initialize_context.py`

## Implementation Plan

### 1. sr-initialize Step 2 context resolution — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests: create `test_initialize_context.py` with a module docstring covering:
   - the harness-rendering model (Claude exact-token substitution, agent placeholder fill)
   - helper stubs `_step2_block(repo_root)`, `_render_claude(block, *, plugin_root, skill_dir)`, `_fill_placeholder(block, skill_dir)`, `_run_block(block, env)`, and fixture-tree builders
   - one empty, documented test per behavior above
2. Stub interface: none. The "interface" is the Step 2 fenced block in `SKILL.md`, and the tests run against the current block first.
3. Write tests and run red: implement the helpers.
   - `_step2_block` returns the single ```` ```bash ```` fence in `SKILL.md` that assigns both `OWNER=` and `APP_DIR=`, asserting there is exactly one.
   - `_run_block` runs `sh -c '<block>\nprintf "%s\n%s\n" "$OWNER" "$APP_DIR"'` with `env={"PATH": …, "HOME": tmp_home, **case_env}` and returns the two values.
   - Implement every case.
   - Run `uv --directory skills/sr-search --no-config run --no-sync pytest tests/test_initialize_context.py -n0` and confirm the cases flagged "Red today" fail against the current block.
4. Write code and run green: rewrite the Step 2 block and its surrounding prose in `skills/sr-initialize/SKILL.md` to the target design.
   - Write `SKILL_DIR="${CLAUDE_SKILL_DIR}"`, plus the placeholder fallback.
   - Compute `APP_DIR` logically.
   - Use braced `${CURSOR_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_ROOT}` tests.
   - Add the `case` path rule, and finish with an `echo "OWNER=$OWNER APP_DIR=$APP_DIR"` line.
   - Write prose that does not depend on the literal token being displayed, since Claude Code substitutes the token everywhere in the body.
   - Replace "Neither env var set means you are in a dev checkout" with the real meaning of each outcome.
   - Re-run the file until green.

### 2. sr-initialize Step 7 owner-aware binding — prose/policy

- Files: `skills/sr-initialize/SKILL.md`
- No tests: prose/policy artifact

1. Replace the "already live → nothing to do" shortcut for harness owners.
   - Always run the guarded `shim install --owner "$OWNER"`: same owner rewrites idempotently, and a foreign live shim gets an honest refusal.
   - Relay a refusal and explain that this harness's session hooks will not refresh a shim another owner holds.
   - Offer `--takeover` (dead engine) or `--takeover --force` (live engine) only with the user's explicit consent.
2. Keep the dev branch (`make shim` from the repo root, owner `dev`). Cover an empty `OWNER` by sending the agent back to Step 2.

### 3. Docs and shared patterns — prose/policy

- Files: `docs/contributing/preparation.md`, `memory-bank/systemPatterns.md`
- No tests: prose/policy artifact

1. `docs/contributing/preparation.md` "Changing the Hooks": say the plugin-root variables exist only for hooks a harness loads from an installed plugin, not for project hooks or agent shells. Copying `hooks/*.json` into a project therefore cannot work.
2. `memory-bank/systemPatterns.md` "Dual-manifest plugin": add one sentence.
   - Plugin-root variables reach harness hook processes only, never agent-run shell commands.
   - A skill finds the engine as its sibling `../sr-search`. Claude Code supplies paths only through exact `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` substitution in skill text.
   - Wrapper skills still carry no paths.
3. Check that `docs/user-guide/troubleshooting/index.md` stays accurate: hooks "can see" the variables, and `sr-initialize` "can see the plugin tree". Change nothing unless the new Step 2 contradicts it.

### 4. Verification and memory

1. Run `make ci`, or the format, lint, test and reuse gates it chains, and read the whole output.
2. Run `claude plugin validate .` and confirm no new warnings.
3. Run `.summem/summem note` with one repo fact: sr-initialize resolves the engine as its sibling and the owner via Claude substitution, Cursor env, the plugins-path rule, or dev; marketplace installs contain `.git` and `Makefile`.

## Technology Validation

No new technology. The one external behavior the design rests on, Claude Code's skill-text substitution, was checked with a headless probe on 2.1.301; results are recorded above.

## Dependencies

- `/bin/sh` on test hosts (CI runs Linux).
- Claude Code's documented skill substitution. The probe fixed the exact-token semantics the test models.

## Challenges & Mitigations

- **Cursor agent-shell behavior is undocumented.** Step 2 does not depend on it: the env check catches an exported variable, and the `.cursor/plugins` path rule catches everything else. Optional UAT for the operator in Cursor: ask the agent to run `echo "[${CURSOR_PLUGIN_ROOT-unset}]"` and run `/sr-initialize` Step 2.
- **Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` everywhere in the body, prose included.** Keep the literal token out of prose that must read correctly in both harnesses; name it in code only.
- **A test that parses `SKILL.md` could drift into a change-detector.** Select the block by behavior (the one fence that assigns `OWNER=` and `APP_DIR=`) and assert only resolved outputs, never wording.
- **Tests run inside harness sessions** (`CLAUDECODE`, maybe `CURSOR_PLUGIN_ROOT` inherited). Pass an explicit minimal `env` to `subprocess.run`.
- **Symlinked homes** (dotfile managers linking `~/.claude`): use logical `pwd` for `APP_DIR` and the path rule, as the hooks' logical `${…}/skills/sr-search` does, so the shim bake matches the hook bake.

## Pre-Mortem

- **The premise is wrong for Cursor** (for example, Cursor substitutes `${CLAUDE_PLUGIN_ROOT}` in skills for Claude compatibility, giving Cursor users `claude`). Mitigation: the Cursor check comes first and uses the braced token, which any such substitution would also fill. The Cursor path rule precedes dev. The UAT line is recorded for the operator.
- **The fix lands, but existing victims keep a mis-owned shim.** Step 7 now runs the guarded install instead of "nothing to do", so a re-run surfaces the foreign owner and offers a consented takeover.
- **"Fix the hooks" was the wrong layer.** The audit shows the hooks are already correct; changing them would add risk with no benefit. Scope keeps hooks unchanged and records why.
- **The "dev" label is still wrong for some real install layout** (a custom Cursor plugin dir outside `~/.cursor/plugins`). With no Cursor env var it would resolve to `dev`. That is acceptable: such layouts are not documented install paths, and the Step 7 dev remedy names `make shim`, which the agent can see does not apply, then fall back to asking. Record it in the reflection if QA finds a real counterexample.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
