# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

**Rework round 3: Claude Code's plugin data folder settles the owner.** Rounds 1 and 2 are complete through Reflect on this branch. Round 2's plan is in git at fc3db1b (`memory-bank/active/tasks.md`), and the history of all rounds is in `progress.md`.

After round 2, Step 2 still asks the Claude Code user who owns a copy that is laid out like an install, sits outside the default plugins folders, and is not listed in the install record. The main case is a contributor's `claude --plugin-dir` checkout at a cache-shaped path. Another is any future change to the record's format. (Native Windows is not helped: Git Bash's `pwd` prints `/c/…` while the substituted data path is `C:/…`, so rule 1 cannot match there and the block asks as before. Preflight advisory 3.)

Claude Code also writes `${CLAUDE_PLUGIN_DATA}` into skill text. Its documented form, `<plugins root>/data/<plugin-id>`, says where the plugin came from:

- For a marketplace install, the folder sits in the same plugins root as the copy's `cache` folder.
- For `--plugin-dir`, the id is `<manifest name>@inline`, so the folder is named `stockroom-inline`.

This round reads that path and settles the owner from it, ahead of the record check. It also reads both pasted paths from a quoted heredoc, so the shell treats them as data and never as code.

Who it helps: Claude Code users in the layouts above. They get no question whenever Claude Code substitutes the token. Cursor users: nothing changes. Cursor substitutes nothing, so both new rules stay silent there.

### Operator decisions (2026-10-17)

- **Use `${CLAUDE_PLUGIN_DATA}`, because it is a documented contract.** The operator: "If the clod plug in data environment variable is documented and it is an actual contract we can adhere to then yes let's go ahead and use it." The docs quoted under Evidence document every part the block relies on.
- **Failure principles.** The operator: "we want to be sure that any way in which it does fail is going to be obvious during initialization so that an intelligent agent can work around it and that any way that it does fail is not going to manifest in any of the deterministic processes without inference."
  1. Every way the new signal can fail must show up during `sr-initialize`, where the agent can work around it.
  2. No failure may reach the processes that run without an agent: the session hooks, `shim rectify`, and the nightly job.
- **Quoting is in scope only because it is cheap.** Folders built by an attacker are not ours to defend against. `'` is the only special character likely to appear in a real folder name, and it already works. The heredoc is still worth it, because it is also what keeps `PLUGIN_DATA` coming only from Claude Code's substitution, never from an inherited environment variable.
- Earlier decisions stand; round 2's plan (fc3db1b) lists them in full:
  - Contributors always get `dev`.
  - Hooks stay as they are.
  - `rectify` replaces a dead shim of any owner.
  - No separate dev data.
  - The install-layout rule is for `sr-initialize` only.
  - No Claude-driven questions for Cursor users.
  - The install record is checked (round 2).

### How the plan meets the failure principles

- **Every new rule only adds a proof.** When the proof is missing or unrecognized, the block falls through to round 2's rules unchanged: the record, then the Cursor root, then an empty owner and the question. The new rule stays silent in each of these failures:
  - The token is not substituted (an older Claude Code, an agent that read the file itself, or another harness). The heredoc line keeps the literal token, and the block clears it.
  - The data path has another shape or lives in another folder.
  - The `--plugin-dir` id is renamed.
- **The failure is visible.** When the `*)` arm falls through, its stderr line now also prints the data folder it was given, or `not given`. The agent and the user can see why the question is asked.
- **No new owner can be wrong:**
  - `claude` needs the data folder to be `data/<id>` in the very plugins root whose `cache/` holds this copy. Only Claude Code's own install layout produces that. A checkout would have to sit inside Claude Code's own cache folder, exactly where Claude Code would put the copy.
  - `dev` needs the folder name `stockroom-inline`. `inline` is a reserved origin name, so no marketplace install can carry it.
- **Processes without an agent are untouched.** The hooks and `shim rectify` neither read `PLUGIN_DATA` nor change. They see only the owner that Step 7 bakes into the shim. Since no new owner can be wrong, nothing new reaches them.
- **Side effect.** The docs say Claude Code creates the data folder when a plugin component first uses it, and deletes it on uninstall from the last scope. Referencing the token may create an empty `data/stockroom-…` folder. Nothing in stockroom reads or writes it.

### Owner rule for this round

- Inside a harness's default plugins folder, the path decides (unchanged).
- A copy laid out like an install (`<x>/cache/<m>/<p>/<v>/skills/sr-search`) anywhere else, in this order:
  1. **New:** `PLUGIN_DATA` is exactly `<x>/data/<some id>` → `claude`.
  2. `<x>/installed_plugins.json` contains the JSON string `"<plugin root>"` → `claude` (round 2).
  3. **New:** the data folder is named `stockroom-inline` → `dev`.
  4. `CURSOR_PLUGIN_ROOT` physically holds this engine → `cursor`.
  5. Otherwise `OWNER` is empty, plus a stderr line. In Claude Code the agent asks the user; in any other harness the agent names its harness.
- Everything else is `dev` (unchanged).

**Why this order.**

- Rules 1 and 2 come before 3, which keeps round 2's outcome for `--plugin-dir` pointed at an install's own copy: `claude`, because that install's hooks keep the shim current. When that copy is in the active plugins root, rule 1 says so. When it is in another root, the record does.
- Rule 3 comes before 4: `stockroom-inline` proves a Claude Code session plugin, while `CURSOR_PLUGIN_ROOT` in an agent shell is undocumented and can leak.
- No test pins the order of rules 2 and 3. Both hold only for `--plugin-dir` pointed at a recorded copy in a plugins root other than the active one. Round 2 left its own order unpinned on the same grounds.

### Evidence that shaped the plan

- **Claude Code docs:**
  - [Plugin loading, "Find where a plugin came from"](https://code.claude.com/docs/en/plugins/loading):
    - "Every plugin has an id of the form `<name>@<origin>`."
    - `@inline` covers `--plugin-dir`, `--plugin-url`, `CLAUDE_CODE_PLUGIN_DIRS` and the Agent SDK `plugins` option.
    - "for `@inline` and `@skills-dir` it's the `name` in the plugin's manifest."
    - "The origin names in this table are reserved, so no marketplace can be named `inline`, `skills-dir`, or `synced`."
  - [Plugin loading, "Find plugins on disk"](https://code.claude.com/docs/en/plugins/loading):
    - One plugins root, `~/.claude/plugins` unless `CLAUDE_CODE_PLUGIN_CACHE_DIR` is set.
    - `cache/<marketplace>/<plugin>/<version>/` holds the copy.
    - `data/<plugin-id>/` is "The plugin's persistent directory, exposed as `${CLAUDE_PLUGIN_DATA}`".
  - [Plugin components, "Reference plugin paths and store data"](https://code.claude.com/docs/en/plugins/components#path-variables-and-persistent-data):
    - The variables are "substituted in skill, command, and agent content".
    - "`<id>` is the plugin identifier with every character other than letters, digits, `_`, and `-` replaced by `-`".
    - "On Windows, the substituted paths use forward slashes."
  - [Manifest reference, "Where each variable resolves"](https://code.claude.com/docs/en/plugins/manifest-reference#where-each-variable-resolves):
    - Skill content: "Anywhere in the Markdown body".
    - "The variables aren't present in the environment of commands Claude runs through the Bash tool".
- **Probes on Claude Code 2.1.302 (2026-10-17).** Real settings, records and data folder were checksummed or listed, and were unchanged after each probe.
  - `${CLAUDE_PLUGIN_DATA}` is substituted in prose and inside a bash fence, for a typed `/plugin:skill` and for a Skill-tool load.
  - `--plugin-dir` from a checkout at `<x>/cache/m/widget/1.0.0` gives `<active plugins root>/data/widget-inline`. The active root followed `CLAUDE_CODE_PLUGIN_CACHE_DIR`.
  - A copied install has its copy at `<R>/cache/livemkt/widget/1.0.0` and its data at `<R>/data/widget-livemkt`: the same root.
  - An in-place local-marketplace load has its root at the source folder, and its data at `<R>/data/widget-localmkt`.
  - The substituted value has no trailing slash.
  - `claude plugin marketplace add` refuses the name `inline` with "Marketplace name "inline" is reserved for --plugin-dir session plugins". It accepts `foo-inline`.
  - In shell-form hooks, the shell expands `"${CLAUDE_PLUGIN_ROOT}"` from the environment: a `$probe` in the folder name survived. So `hooks/claude-hooks.json` has no quoting problem, and no hook changes.
  - Scripts:
    - `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/plugin_data_probe.sh`
    - `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/hook_quote_probe.sh`
- **Quoting prototype.** 9 folder names, each run under dash, bash and BusyBox sh.
  - Today's block:
    - `$x`, `\$` and pairs of `"` silently change the path.
    - A lone `"` is a syntax error.
    - A backtick, `$(…)` or `";…;"` runs a command.
  - The heredoc variant reads all 9 correctly, and still falls back to the placeholder when nothing is substituted.
  - Script: `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/quoting_demo.sh`, with its helpers `render_block.py` and `make_variant.py` in the same folder.

### Target design

The head of the Step 2 block (replaces today's lines 31 and 32):

```bash
{ IFS= read -r SKILL_DIR; IFS= read -r PLUGIN_DATA; } <<'SR_PATHS'
${CLAUDE_SKILL_DIR}
${CLAUDE_PLUGIN_DATA}
SR_PATHS
case "$SKILL_DIR" in ''|'$'*) SKILL_DIR="<POSIX absolute path of the directory holding this SKILL.md>" ;; esac
case "$PLUGIN_DATA" in '$'*) PLUGIN_DATA="" ;; *?/) PLUGIN_DATA="${PLUGIN_DATA%/}" ;; esac
```

The `*)` arm:

```bash
    *)
      if [ "$PLUGIN_DATA" = "${CACHE_DIR%/*}/data/${PLUGIN_DATA##*/}" ] || grep -qF -- "\"$PLUGIN_ROOT\"" "${CACHE_DIR%/*}/installed_plugins.json" 2>/dev/null; then OWNER=claude
      elif [ "${PLUGIN_DATA##*/}" = stockroom-inline ]; then OWNER=dev
      elif [ -n "$CURSOR_APP" ] && [ "$CURSOR_APP" = "$REAL_APP" ]; then OWNER=cursor
      else printf 'sr-initialize: %s is laid out like an installed plugin outside the default plugins folders, but no install record lists it and the plugin data folder (%s) is not in its plugins root\n' "$APP_DIR" "${PLUGIN_DATA:-not given}" >&2
      fi ;;
```

- **The heredoc.** With a quoted delimiter, the shell expands nothing in the two body lines, so it reads Claude Code's pasted paths byte for byte. A newline in the path would break the read; AC8 already excludes such paths. The values can only come from substitution, never from an environment variable. `IFS=` keeps leading and trailing spaces, and `-r` keeps backslashes.
- **When nothing is substituted.** The body still holds the literal tokens, which start with `$`; a real path never does. The `case` lines turn the skill line into the placeholder, as today, and clear the data line. The patterns never spell out a whole token, so Claude Code's text replacement leaves them alone.
- **A trailing `/` is dropped.** The docs write the folder as `data/<plugin-id>/`, while 2.1.302 substitutes it without one.
- **Rule 1 compares the whole path.** An empty value never matches (the right side ends in `/data/`). Neither does a data folder in another plugins root, a seed folder or a nested folder.
- **Rule 3 compares the whole folder name** with `stockroom-inline`, the docs' sanitized form of `stockroom@inline`. A marketplace named `foo-inline` gives `stockroom-foo-inline`, which does not match.
- **No sanitizing is re-applied.** Rule 1 does not depend on the id at all.

## Test Plan (TDD)

### Behaviors to Verify

All cases are in `test_initialize_context.py`. Each runs under `sh`, `bash` and `zsh` where installed, and reads its result back through the printed line, as in rounds 1 and 2.

**Unit 1: Claude Code's paths are read as data.**

- **A pasted path with shell characters is read as written.** A `--plugin-dir` checkout at `<tmp>/<name>/stockroom`, Claude rendering, gives `("dev", <checkout>/skills/sr-search)`. No file named `ran` appears in the run's working folder. Folder names, parametrized:
  - `cost$x` (id `dollar`). Red today: the path loses `$x`, so the block finds no engine.
  - `` tick`touch ran`tock `` (id `backtick`). Red today: `touch` runs, then no engine is found.
  - `one"quote` (id `double-quote`). Red today: a syntax error, and nothing is printed.
- **Unchanged and still green:**
  - Every existing test, including the `'` cases (`test_printed_line_survives_quotes_in_the_path`, `test_claude_recorded_install_with_quotes_in_the_path`).
  - The placeholder-filled cases.
  - `test_unfilled_placeholder_resolves_nothing`: the block run as written still finds nothing.

**Unit 2: the data folder settles the owner.**

- **Unrecorded custom-root install, found by its data folder.** The copy is at `<tmp>/plugin-cache/cache/txrk9/stockroom/2.1.1` with no record, and the data folder is `<tmp>/plugin-cache/data/stockroom-txrk9`, parametrized with and without a trailing `/` (ids `no-slash`, `trailing-slash`) → `claude`. Red today: `""`.
- **`--plugin-dir` checkout at a cache-shaped path.** The checkout is at `<tmp>/src/cache/acme/widgets/stockroom`. The data folder is `<home>/.claude/plugins/data/<name>-inline`, where `<name>` is read from `.claude-plugin/plugin.json` → `dev`. Red today: `""`. Reading the manifest name makes a plugin rename turn this test red, because rule 3 spells the name out.
- **A data folder in another plugins root proves nothing.** The copy is at `<tmp>/seed/cache/<mkt>/stockroom/2.1.1` with no record. The data folder is `<home>/.claude/plugins/data/stockroom-<mkt>`, parametrized over `<mkt>` = `txrk9` and `acme-inline` → `""`. Green today. It guards rule 1's whole-path match and rule 3's whole-name match: `acme-inline` must not count as a session plugin.
- **An inherited `CLAUDE_PLUGIN_DATA` variable labels nothing.** A placeholder-filled (Cursor) rendering of a copy at `<tmp>/elsewhere/cache/txrk9/stockroom/672cf3aa`, with `CLAUDE_PLUGIN_DATA=<tmp>/other/data/stockroom-inline` in the shell's environment → `""`. Green today. It guards "values come only from substitution".
- **Without the data token** (`plugin_data` not given), the existing Claude renderings model a Claude Code that did not substitute it, and keep round 2's outcomes:
  - `test_claude_custom_plugins_root_gets_no_owner` → `""`.
  - `test_checkout_in_a_cache_shaped_path_gets_no_owner` → `""`.
  - `test_leaked_cursor_root_is_ignored` → `""`.
  - Their docstrings say they cover that case.

**Mutation check** (run as a script on a scratch copy of the repo, never in the worktree):

- M1: the head goes back to double-quoted assignments (`SKILL_DIR="${CLAUDE_SKILL_DIR}"`, `PLUGIN_DATA="${CLAUDE_PLUGIN_DATA}"`) → the three shell-character cases and the inherited-variable case go red.
- M2: rule 1 deleted → both data-folder install cases go red.
- M3: rule 1 loosened to "any data folder" (`case "$PLUGIN_DATA" in */data/?*)`) → both other-root cases and the `--plugin-dir` cache-shaped case go red (preflight advisory 1).
- M4: rule 3 loosened to `*-inline` → the `acme-inline` other-root case goes red.
- M5: rule 3 deleted → the `--plugin-dir` cache-shaped case goes red.

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`
- Conventions in `test_initialize_context.py`:
  - A module docstring that states the owner rule, and a docstring on every test.
  - The `shell`, `step2` and `home` fixtures, plus `repo_root` from `conftest.py`.
  - The helpers `_render_claude`, `_fill_placeholder`, `_run_block`, `_plugin_tree`, `_checkout_tree` and `_record_install`.
  - Subprocesses run with an explicit minimal environment.
- Helper changes:
  - `_step2_block` selects the one bash fence that holds `${CLAUDE_SKILL_DIR}`. It no longer looks for a line starting `SKILL_DIR=`, because the block now reads that value with `read`.
  - `_render_claude` gains `plugin_data: Path | str | None = None`. When given, it replaces `${CLAUDE_PLUGIN_DATA}`.
- New test files: none.

## Implementation Plan

### 1. Step 2 reads Claude Code's pasted paths as data — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests:
   - `_step2_block`: select the one bash fence holding the `${CLAUDE_SKILL_DIR}` token, and update its docstring and assertion message. Today's block still matches, so every existing test stays green.
   - `_run_block`: run the readback with `cwd=home`, like the block (preflight advisory 7).
   - Add `test_skill_path_is_read_as_data`, parametrized over the three folder names with ids `dollar`, `backtick` and `double-quote`, with an empty, documented body.
2. Stub interface: none. The interface is the Step 2 fence.
3. Write tests and run red:
   - Implement the test: `_checkout_tree(tmp_path / name / "stockroom")`, render with `_render_claude`, and assert `("dev", <checkout>/skills/sr-search)` and that `tmp_path / "ran"` does not exist.
   - Run `uv run --no-sync --no-config pytest tests/test_initialize_context.py -n0` from `skills/sr-search` and read the whole output. Expected red set: the 3 cases under sh and bash (6 failures). Every existing case stays green.
4. Write code and run green:
   - Replace lines 31 and 32 of the Step 2 fence with the single-value form of the target head:
     - `IFS= read -r SKILL_DIR <<'SR_PATHS'`
     - `${CLAUDE_SKILL_DIR}`
     - `SR_PATHS`
     - the `SKILL_DIR` `case` line from the target design.
   - Re-run until green under every installed shell.
   - Update the scratch BusyBox check, `busybox-step2-check.sh`, to render through `render_block.py`, which selects the fence by its token. Run it against the worktree's `SKILL.md` and expect `PASS`.

### 2. Step 2 settles the owner from Claude Code's data folder — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests:
   - Add empty, documented tests:
     - `test_claude_custom_root_install_by_data_folder`, parametrized over the suffix `""` / `"/"`, with ids `no-slash` and `trailing-slash`.
     - `test_claude_plugin_dir_checkout_in_a_cache_shaped_path_is_dev`
     - `test_data_folder_in_another_plugins_root_proves_nothing`, parametrized over `txrk9` and `acme-inline`.
     - `test_leaked_plugin_data_variable_is_ignored`
   - Modify the existing docstrings:
     - The module docstring:
       - Claude Code also substitutes `${CLAUDE_PLUGIN_DATA}` (plugin skills only) as `<plugins root>/data/<plugin-id>`.
       - The second owner-rule bullet now starts with the data folder: in the copy's plugins root → `claude`; named `stockroom-inline` → `dev`. Then come the record and the Cursor root.
     - `test_claude_custom_plugins_root_gets_no_owner`, `test_checkout_in_a_cache_shaped_path_gets_no_owner` and `test_leaked_cursor_root_is_ignored`: add that Claude Code did not substitute its data folder. Their expectations are unchanged.
2. Stub interface: none (the fence).
3. Write tests and run red:
   - `_render_claude` gains the keyword `plugin_data`, replacing `${CLAUDE_PLUGIN_DATA}` with `str(plugin_data)` when given. Update its docstring.
   - Implement the four tests per the behaviors above. The `--plugin-dir` test takes the `repo_root` fixture and reads `name` from `.claude-plugin/plugin.json`.
   - Run red and read the whole output. Expected red set: the two data-folder install cases and the `--plugin-dir` case, under sh and bash (6 failures). The other-root cases, the inherited-variable case and every existing case stay green.
4. Write code and run green:
   - In the head, replace the single `read` with the two-value form from the target design, and add the `PLUGIN_DATA` `case` line.
   - Replace the `*)` arm with the target arm, verbatim.
   - Re-run until green under every installed shell.
   - Mutation check M1 to M5. Write a new scratch script, `mutation_check_r3.py`, modeled on round 2's `mutation_check.py`, and run it on a scratch copy. Each mutant must turn red exactly the tests listed for it, and the unmutated copy must pass.
   - Re-run the BusyBox check and expect `PASS`.

### 3. Step 2 prose in `SKILL.md` — prose/policy

- Files: `skills/sr-initialize/SKILL.md`
- No tests: prose/policy artifact

1. The "Run this block as written" paragraph: Claude Code writes this skill's directory and the plugin's data folder into the block when it loads the skill. In any other harness, replace only the angle-bracket placeholder, and leave the rest of the block as written.
2. The `claude` or `cursor` owner bullet, custom-folder sentence: a Claude Code install in a custom plugins folder also counts. Either the plugin data folder that Claude Code writes into the block sits in the same plugins root as the copy (`data/` beside `cache/`), or Claude Code's install record lists the copy. Keep the Cursor sentence.
3. The `dev` bullet: keep it. `--plugin-dir` is already listed.
4. The empty-`OWNER` bullet: "laid out like an installed plugin, outside the default plugins folders, and nothing proves who installed it."
   - The Claude Code sub-bullet: this happens only when Claude Code did not write its paths into the block (for example, the file was read by hand), or the copy is not in the plugins root Claude Code uses (for example, a seed folder mounted elsewhere). The block's stderr line shows the data folder it was given. Keep the question and "Never pick it yourself."
   - The other-harness sub-bullet: unchanged.
5. Step 7: no change. Its mislabel row already defers to the owner the block printed for the same path.

### 4. Shared patterns, brief and repository memory — prose/policy

- Files: `memory-bank/systemPatterns.md`, `memory-bank/active/projectbrief.md`, `.summem/notes/*` (written only through `.summem/summem note`)
- No tests: prose/policy artifact

1. `systemPatterns.md`, the plugin-root paragraph under Dual-manifest:
   - The substitution sentence names `${CLAUDE_PLUGIN_DATA}` beside `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_ROOT}`.
   - The owner-rule sentence: outside the default folders, an install-shaped copy is `claude` when Claude Code's data folder for it (`data/<plugin-id>`) sits in the copy's plugins root, or when the install record lists its exact path. It is `dev` when the data folder is `stockroom-inline` (a `--plugin-dir` load), and `cursor` when `CURSOR_PLUGIN_ROOT` holds it.
   - Keep "The substituted `${CLAUDE_PLUGIN_ROOT}` is not proof".
2. Brief AC7: outside the default folders, Claude Code's substituted plugin root is not proof, but its plugin data folder and its install record are. The rest follows the owner rule above. Otherwise the agent asks the user. Also update AC3's cache-shaped exception and UC3 (preflight advisory 2). A Claude Code checkout there now gets `dev` from its data folder. The question remains only when Claude Code did not substitute the folder. Cursor's accepted residual is unchanged.
3. Add a new brief AC10 for the operator's failure principles: when the substituted data folder is missing, renamed or moved, the outcome falls back to round 2's. Any such failure shows up during `sr-initialize`, as the question plus a stderr line, and never as an owner that the hooks would act on.
4. Add two `.summem/summem note`s, and follow any nap request the tool prints:
   - The round 3 owner rule. It supersedes the round 2 owner-rule note.
   - Step 2 now reads both pasted paths from a quoted heredoc. It supersedes the 2026-10-17 quoting note (preflight advisory 5).
5. Docs under `docs/`: no change. A grep during planning found no statement of the owner rule there.

### 5. Verification

1. Run `make ci` from the repo root and read the whole output.
2. Run `claude plugin validate .` and confirm no new warnings.
3. **Live end-to-end check** on Claude Code, as a scratch script, `live_step2_check.sh`. It loads the worktree's real `sr-initialize` and runs the Step 2 fence that Claude Code rendered, taken from the session transcript.
   - Session settings:
     - Haiku with `--tools ""` (no tools) and `--max-turns 1`.
     - `--settings '{"disableAllHooks": true}'`.
     - A scratch plugins root (`CLAUDE_CODE_PLUGIN_CACHE_DIR`) and a scratch project.
   - Real settings and records are checksummed before and after, and `~/.claude/plugins/data` is listed before and after.
   - Each session also loads the scratch `widget` plugin. If its SessionStart hook leaves no `hook-out.txt`, hooks really were off.
   - Load A: `--plugin-dir` from a copy of the tracked files, placed at `<scratch>/A-checkout/cache/m/stockroom/x` → `dev`.
   - Load B: a copied install, from a `url`-source marketplace over a one-commit git repo of the same files, at `--scope local` → `claude`. The session runs with the record present, because Claude Code does not load the plugin without it. Run the rendered fence once as is. Then move `installed_plugins.json` aside and run it again, so that only rule 1 can prove the owner (preflight advisory 4).
   - Run each rendered fence under sh and bash. Check `OWNER`, `APP_DIR` (the expected copy's `skills/sr-search`), and that the rendered fence holds the heredoc with both paths filled in.
4. The live shim is baked to `~/git/stockroom`, so the pre-commit `make format` sync of this worktree changes nothing outside it. Confirm with `grep '^# STOCKROOM_' ~/.local/bin/stockroom`.

## Technology Validation

No new technology - validation not required. The heredoc, `read -r`, `case` and `${…%…}` / `${…##…}` are POSIX. The heredoc variant was prototyped under dash, bash and BusyBox sh (Evidence).

## Dependencies

- Claude Code substitutes `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PLUGIN_DATA}` anywhere in a plugin skill's Markdown body. This is documented, and verified on 2.1.302 inside a fence.
- The documented plugins-root layout: `cache/<marketplace>/<plugin>/<version>/` and `data/<plugin-id>/` under one root.
- The documented plugin id `<manifest name>@inline` for `--plugin-dir` loads, and its reserved origin names.
- `grep -qF --` for the round 2 record check (unchanged).

## Challenges & Mitigations

- **Substitution inside the heredoc.** Claude Code replaces text anywhere in the Markdown body, and the probes saw it inside a fence. The live check confirms it on the real file. If it does not substitute there, stop: that is the circuit breaker, so report rather than rework.
- **An agent copies the block badly.** If the closing `SR_PATHS` gets indented, the heredoc never ends and swallows the block, so nothing is printed. That failure is obvious, and Step 2 already says what to do when no line is printed. "Run this block as written" stays the instruction.
- **A Cursor agent fills the heredoc lines itself.** The prose says to replace only the placeholder. A skill path pasted into the first line still works. A made-up data path matches rule 1 only if it is exactly Claude Code's own layout for this copy.
- **`_fill_placeholder` replaces every `<…>` on one line.** The new lines hold no `<` and `>` on one line except the placeholder. `<<'SR_PATHS'` has no `>`.
- **Fence selection.** The `${CLAUDE_SKILL_DIR}` token must appear in exactly one fence. `_step2_block` asserts that.
- **A plugin rename.** Rule 3 spells out `stockroom-inline`. The `--plugin-dir` test reads the manifest name, so a rename turns it red.
- **Older Claude Code without the data substitution.** The literal token is cleared, and round 2's outcomes apply. The existing Claude-rendered tests pin that.
- **Seeds, and synced copies under a custom root.** Seeds load their copies in place from the seed folder, and their data folder is elsewhere, so they fall through as in round 2. Synced copies under a custom root stay `dev` (round 2 advisory 4, accepted). Both are out of scope for this round.
- **zsh is still never run**, here or in CI (carried).

## Pre-Mortem

- **The premise is wrong: an install's data folder is not always in its copy's plugins root.** The docs table and probe B say it is for copied installs. In-place and seed loads keep their data elsewhere and fall through, so the worst outcome is round 2's question. The live check with the record moved aside tests the premise on the real file.
- **The tests model Claude Code's rendering, and Claude Code renders differently.** That was round 2's lesson: the tests write both sides of the premise. Verification step 3 renders the real `SKILL.md` through Claude Code and runs that output. It is part of the plan, not optional.
- **A reviewer finds the heredoc odd.** Answer in the PR: it reads pasted paths as data, and it is the reason `PLUGIN_DATA` can come only from Claude Code. Explain in the PR, not in comments inside the block, because the block has none today.
- **The live check touches the user's real setup.** It runs with no tools, hooks off (proved by the widget plugin), and scratch plugins roots. Real records and the data folder are checked before and after. Each session writes only a transcript under `~/.claude/projects/`, as round 2's probes did.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight (PASS WITH ADVISORY)
- [ ] Build
- [ ] QA

## Build progress

- [x] 1. Step 2 reads pasted paths as data:
    - Red: 6 failed (3 folder names × sh and bash), 48 passed.
    - Green: 54 passed, 27 skipped (zsh absent).
    - BusyBox check (preflight's `busybox_target_check.sh`): `dollar`, `backtick` and `dquote` PASS. `data` and `inline` FAIL, as expected before Unit 2.
- [x] 2. Step 2 settles the owner from the data folder:
    - Red: 6 failed (the two data-folder install cases and the `--plugin-dir` case, × sh and bash), 60 passed.
    - Green: 66 passed, 33 skipped (zsh absent).
    - Mutation check (`scratchpad/scripts/mutation_check_r3.py`, on scratch copies): unmutated 0; M1 8; M2 4; M3 6; M4 2; M5 2. Each is exactly its predicted set: ALL OK.
    - BusyBox check: all 5 cases PASS (`data`, `inline`, `dollar`, `backtick`, `dquote`).
- [x] 3. Step 2 prose:
    - The run paragraph: Claude Code writes the skill directory and the data folder; replace only the placeholder.
    - The custom-folder sentence: the data folder or the install record.
    - The empty-`OWNER` bullet, and its Claude Code sub-bullet with when it happens and where the error line shows the data folder.
    - Step 7 unchanged. The tokens appear only in the fence (grep).
- [x] 4. Patterns, brief and SumMem:
    - `systemPatterns.md`: the tokens sentence, the heredoc, and the owner rule.
    - Brief: UC3, AC3 and AC7, plus a new AC10 (failure principles).
    - SumMem: the round 3 owner-rule note and the heredoc note, plus the naps the tool asked for.
- [ ] 5. Verification

## Preflight advisories: dispositions

- **1 (M3 also turns the `--plugin-dir` case red):** applied in the mutation list.
- **2 (brief AC3 and UC3 go stale):** applied in Unit 4. AC3's cache-shaped exception and UC3 are updated along with AC7.
- **3 (native Windows cannot match rule 1):** applied. The claim is dropped from the description. Native Windows falls back to the question, as before.
- **4 (live check details):** applied in Unit 5.
    - The session runs with the record present. The record is moved aside only before the second run of the rendered fence.
    - Each run also checks `APP_DIR` and that the rendered fence holds the heredoc.
- **5 (stale SumMem quoting note):** applied in Unit 4, as a second note: Step 2 now reads both paths from a quoted heredoc.
- **6 (`--plugin-dir` leaves an empty `data/stockroom-inline` folder):** for the PR text, noted for Reflect.
- **7 (`_run_block` readback `cwd`):** applied in Unit 1. The readback runs with `cwd=home`, like the block.
- **8 (reuse preflight's scripts):** applied. Build renders through preflight's `render_both.py` and runs its `busybox_target_check.sh`. `mutation_check_r3.py` follows its `run_variants.py`.
- **Design idea (a `PROOF` field in the printed line):** not applied. It changes the printed interface and every expected result, to pin an order that no real copy exercises. The operator asked not to get lost in the weeds. It is left for the operator.
