# Task: plugin-root-resolution

* Task ID: plugin-root-resolution
* Complexity: Level 2
* Type: bug fix

**Rework round 2: Claude Code's install record proves a custom-folder install.** Round 1 (the PR #142 review fixes) went through plan, preflight, Build, QA PASS and Reflect on this branch. Its plan is in git at 50835fd (`memory-bank/active/tasks.md`), and its history is in `progress.md`.

Round 1 made every install-shaped copy outside the default plugins folders ask the Claude Code user for its owner. The reason: `claude --plugin-dir` substitutes a checkout exactly as an install is substituted, so substitution proves nothing. This round lets Claude Code's own install record answer instead. When `installed_plugins.json`, in the plugins root that holds the copy's `cache` folder, lists the copy's exact path, the copy is a Claude Code install: `OWNER=claude`, with no question.

Who it helps: Claude Code users who set `CLAUDE_CONFIG_DIR` (unless that folder is named `.claude`) or `CLAUDE_CODE_PLUGIN_CACHE_DIR`. Round 1 would ship them a question during `sr-initialize`. This round removes it for every recorded install, before it is ever released. It does not help claude.ai-synced copies under a custom plugins root (`<root>/synced/…`): synced plugins have no install record, so they stay `dev`, and Step 7 still stops and asks, because the path is not the user's checkout (preflight advisory 4).

### Operator decisions (2026-10-16)

- **Contributors always get `dev`.** A marketplace install must be recognizable as a real install. Anything run from a checkout with intent to develop or iterate is `dev`. That covers `claude --plugin-dir`, Cursor `~/.cursor/plugins/local/`, local-path marketplaces loaded in place, and the Cursor localdev mirror.
- **Hooks stay as they are.** Option B, `rectify` doing nothing on dev loads, is rejected: a dev session's hook must still be able to heal the checkout.
- **`rectify` replaces a dead shim, whoever owns it.** Approved.
- **No separate dev data (option E rejected).**
- **Argument substitution is not a concern.** None of our skills take arguments; the Step 2 block uses no positional tokens.
- **Option A, the install-layout rule, is for `sr-initialize` only.**
- **PR #142 review: fix all six findings in this PR.** Done in round 1.
- **No Claude-driven questions for Cursor users:** "We do not want Cursor users to have to answer extra questions to account for Claude Code situations."
- **Install record in this PR (rework round 2).** The version-folder plan review recommended the install-record check as a follow-up after PR #142. The operator asked "Why not as part of this PR?", asked for the false-positive risk to be checked, and then invoked `/niko-plan then!`. The version-folder proof itself stays rejected (review verdict: revise).

### Owner rule for this round

Only the second bullet's first sub-bullet is new:

- Inside a harness's default plugins folder, the path decides. `claude`: `…/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` and `…/.claude/plugins/synced/…`. `cursor`: `…/.cursor/plugins/cache/…`.
- A copy laid out like an install (`<x>/cache/<m>/<p>/<v>/skills/sr-search`) anywhere else:
  - **New:** `<x>/installed_plugins.json` contains the JSON string `"<plugin root>"` → `claude`.
  - `CURSOR_PLUGIN_ROOT` physically holds this engine → `cursor`.
  - Otherwise `OWNER` is empty. In Claude Code the agent asks the user (`dev` or `claude`); in any other harness the agent names its harness.
- Everything else is `dev`.

**Why the record check comes first.** Claude Code writes the record itself, and its docs describe it. `CURSOR_PLUGIN_ROOT` in agent shells is undocumented, and a CLI bug can leak another plugin's root into it. The order only matters for a copy that Claude Code records and that is also the Cursor root, and no such copy exists in practice. So no test pins the order.

**Cost, stated plainly.** No new question anywhere. One outcome changes, with no question: a Cursor agent that reads a recorded Claude Code custom-folder copy now gets `claude`, where it used to name `cursor`. The default-folder rule already gives `claude` for `~/.claude/plugins/cache/…` read from Cursor, so the two now agree.

**How it fails.** Any mismatch leaves `OWNER` empty, which is round 1's behavior: a path stored escaped in the JSON (`"`, `\`, control characters, native Windows `C:\\…`), a missing or unreadable record, or a future change to the record. It never gives a harness label to a copy whose exact path is not a string in the record. The match ignores which key holds the string: a `projectPath` equal to the copy's path also matches, but that needs a checkout inside Claude Code's own cache folder (preflight advisory 3, accepted).

**Accepted residual (Cursor), unchanged from round 1.** A checkout whose real path has a `cache/<a>/<b>/` shape, read through that path with no `CURSOR_PLUGIN_ROOT`, still gets `cursor` from the agent.

### Evidence that shaped the plan

- **Claude Code docs, [plugin loading](https://code.claude.com/docs/en/plugins/loading):**
  - The plugins-root table: `installed_plugins.json` "records each install with its `scope`, `installPath`, and `version`". The plugins root is `~/.claude/plugins` unless `CLAUDE_CODE_PLUGIN_CACHE_DIR` is set.
  - "In-place and copied plugins": `--plugin-dir`, skills-directory plugins, and relative-path plugins in a marketplace added from a local path load in place. Every other marketplace plugin is copied into `cache/<marketplace>/<plugin>/<version>/`, and that copy loads.
  - An update or uninstall writes `.orphaned_at` into the old version folder, which is removed 14 days later.
- **Probes on Claude Code 2.1.302 (scratch; the real `~/.claude` settings and records checksummed unchanged):**
  - `CLAUDE_CONFIG_DIR=<d>` puts the plugins root at `<d>/plugins`; `CLAUDE_CODE_PLUGIN_CACHE_DIR=<d>` puts it at `<d>`. Either way the record sits beside `cache/`, at `${CACHE_DIR%/*}/installed_plugins.json` in the block's terms.
  - Directory marketplaces with relative-path plugins (a git repo, a plain folder, and a self-hosting checkout with `"source": "./"` placed at a cache-shaped path) get a cache entry and a record. But `claude plugin list --json` reports `readFromFolder` = the source folder, so they load in place. The checkout path appears only in `known_marketplaces.json` and settings, never as an `installPath`.
  - An update from 1.0.0 to 1.0.1 moves `installPath` to 1.0.1 and marks 1.0.0 `.orphaned_at`. The check calls 1.0.0 unrecorded.
  - A copied (`url`-source) plugin at `--scope local`, with the plugins root reached through a symlink: the record keeps the symlinked path as given. A live headless session substituted `${CLAUDE_SKILL_DIR}` as `<installPath>/skills/where` and `${CLAUDE_PLUGIN_ROOT}` as `<installPath>`, which the session transcript confirms. The block's logical `cd` and `pwd` keep that string under dash and bash, and the check finds it.
  - On this machine, `visual-explainer/0.8.1` is recorded, and the orphaned `txrk9-agent-plugins/stockroom/0.16.0` is not.
- **Prototype (scratch copy of the repo):**
  - The target block passes every existing Step 2 test under sh and bash (zsh is absent), plus the draft cases below.
  - Against today's block, the draft cases fail exactly as planned: 8 failures, 4 tests × 2 shells.
  - A mutant without the quotes around the pattern turns the orphan case red.
  - Under BusyBox sh, with BusyBox `grep` and `sed`, a recorded copy under `O'Brien files/plugins` gives `claude` through the printed line. Script: `/tmp/claude-1000/-home-mobaxterm-worktrees-Texarkanine-stockroom-stockroom-claudeboarding/3b628427-7950-4f51-90b9-cfcc5ad0911b/scratchpad/scripts/busybox-step2-check.sh <SKILL.md> <new work dir>`, with its helper `render_step2.py` beside it.

### Target design

Only the `*)` arm of the Step 2 block changes:

```bash
    *)
      if grep -qF -- "\"$PLUGIN_ROOT\"" "${CACHE_DIR%/*}/installed_plugins.json" 2>/dev/null; then OWNER=claude
      elif [ -n "$CURSOR_APP" ] && [ "$CURSOR_APP" = "$REAL_APP" ]; then OWNER=cursor
      else printf 'sr-initialize: %s is laid out like an installed plugin, but outside the default plugins folders and no install record lists it\n' "$APP_DIR" >&2
      fi ;;
```

- The quotes around the pattern make it match one whole JSON string value, so `…/2.1.1` never matches `…/2.1.10`.
- `-F` reads the path literally, and `--` ends options. A missing record makes `grep` exit 2, which counts as "not listed".
- The match ignores the record's nesting, key order and indentation.

## Test Plan (TDD)

### Behaviors to Verify

All cases are in `test_initialize_context.py`. Each runs under `sh`, `bash` and `zsh` where installed, and reads the result back through the printed line, as in round 1.

- **Recorded custom-folder install, Claude rendering, two layouts.** `CLAUDE_CONFIG_DIR` shape: plugins root `<tmp>/claude-work/plugins`. `CLAUDE_CODE_PLUGIN_CACHE_DIR` shape: plugins root `<tmp>/plugin-cache`. Each has a copy at `<root>/cache/txrk9/stockroom/2.1.1` and a record listing it → `("claude", <copy>/skills/sr-search)`. Red today: `""`.
- **Recorded install with the placeholder filled** (no substitution: a Cursor agent reading Claude Code's copy, or an older Claude Code) → `claude`. Red today: `""`.
- **Recorded install whose path holds `'` and a space** (`<tmp>/O'Brien files/claude/plugins/…`) → `claude`. Red today: `""`.
- **Orphaned copy.** Copy `2.1.1` carries `.orphaned_at`, and the record lists only `2.1.10` → `("", <copy>/skills/sr-search)`. Green today. It guards the whole-string match: the unquoted-pattern mutant turns it red.
- **Unchanged and still green:**
  - `test_claude_custom_plugins_root_gets_no_owner` (no record) → `""`.
  - `test_checkout_in_a_cache_shaped_path_gets_no_owner` → `""`.
  - `test_leaked_cursor_root_is_ignored` → `""`.
  - `test_cursor_custom_cache_with_env` → `cursor`.
  - `test_unattributed_install_has_no_owner` → `""`.
  - Every default-folder, `dev`, missing-engine and unfilled-placeholder case.

### Test Infrastructure

- Framework: pytest + pytest-xdist, configured in `skills/sr-search/pyproject.toml`; run through `make test`.
- Test location: `skills/sr-search/tests/`
- Conventions in `test_initialize_context.py`:
  - A module docstring that states the owner rule, and a docstring on every test.
  - The `shell`, `step2` and `home` fixtures.
  - The `_render_claude`, `_fill_placeholder`, `_run_block`, `_plugin_tree` and `_checkout_tree` helpers.
  - Subprocesses run with an explicit minimal env.
- New test files: none. New helper: `_record_install(plugins_root, *install_paths)`.

## Implementation Plan

### 1. Step 2: Claude Code's install record labels a custom-folder copy — executable

- Files: `skills/sr-search/tests/test_initialize_context.py`, `skills/sr-initialize/SKILL.md`

1. Stub tests:
   - Add empty, documented tests:
     - `test_claude_recorded_custom_root_install`, parametrized over `plugins_root` with ids `config-dir` and `cache-dir`.
     - `test_claude_recorded_install_without_substitution`
     - `test_claude_recorded_install_with_quotes_in_the_path`
     - `test_claude_orphaned_custom_root_copy_gets_no_owner`
   - Modify the existing docstrings:
     - The module docstring's second owner-rule bullet: an install-shaped copy elsewhere is `claude` when Claude Code's install record lists its exact path, and `cursor` when `CURSOR_PLUGIN_ROOT` holds it. Otherwise it gets no owner.
     - `test_claude_custom_plugins_root_gets_no_owner`: "with no install record listing it". Its expectation is unchanged.
2. Stub interface: none. The interface is the Step 2 fence.
3. Write tests and run red:
   - Add `import json` and the helper `_record_install(plugins_root: Path, *install_paths: Path) -> None`. It writes `installed_plugins.json` into the plugins root, beside `cache/`, shaped as Claude Code 2.1.302 writes it:
     - `{"version": 2, "plugins": {"stockroom@txrk9": [{"scope": "user", "installPath": …, "version": …}]}}`
     - `json.dumps(indent=2, ensure_ascii=False)`, as Node writes it.
   - Implement the four tests per the behaviors above.
   - Run `pytest tests/test_initialize_context.py -n0` and read the whole output. Expected red set: the two layouts, the placeholder case and the quotes case, under sh and bash (8 failures). The orphan case and every existing case stay green.
4. Write code and run green:
   - Replace the `*)` arm in the Step 2 fence with the target arm, verbatim.
   - Edit the `claude` or `cursor` owner bullet. Add: a Claude Code install in a custom plugins folder (`CLAUDE_CONFIG_DIR` or `CLAUDE_CODE_PLUGIN_CACHE_DIR`) also counts when Claude Code's install record, `installed_plugins.json` beside its `cache` folder, lists it.
   - The empty-`OWNER` bullet: "outside the default plugins folders, and no install record lists it." The Claude Code sub-bullet keeps the question. Its reason becomes: Claude Code's install record does not list it, and `claude --plugin-dir` makes a checkout look the same as an install here.
   - Re-run until green under every installed shell.
   - Mutation check. Run it as a script under `scratchpad/scripts/`, in a scratch copy of the repo, never in the worktree:
     - Drop the pattern's quotes → the orphan case goes red.
     - Delete the record branch → the three recorded cases go red.
   - Re-run the BusyBox check script named under Evidence against the worktree's `SKILL.md`, and expect `PASS`.

### 2. Step 7: skip the checkout question for a proven install — prose/policy

- Files: `skills/sr-initialize/SKILL.md`
- No tests: prose/policy artifact

1. The mislabel row asks first whether a path outside the default plugins folders is a checkout. Add one sentence to it: if that path is the `APP_DIR` that Step 2 just labelled `claude` or `cursor`, it is an install, so skip that question. Consent for `--takeover --force` is still required.
2. No other Step 7 change.

### 3. Shared patterns, brief and repository memory — prose/policy

- Files: `memory-bank/systemPatterns.md`, `memory-bank/active/projectbrief.md`, `.summem/notes/*` (written only through `.summem/summem note`)
- No tests: prose/policy artifact

1. `systemPatterns.md`, Dual-manifest paragraph. Replace "Elsewhere, an install-shaped copy (…) is `cursor` when `CURSOR_PLUGIN_ROOT` holds it." with: "Elsewhere, an install-shaped copy (…) is `claude` when Claude Code's install record (`installed_plugins.json` in the plugins root, beside `cache/`) lists its exact path, and `cursor` when `CURSOR_PLUGIN_ROOT` holds it."
2. Brief AC7: Claude Code's substituted plugin root is not proof, but its install record is. A copy whose exact path `installed_plugins.json` lists gets `claude` with no question. Otherwise the agent asks the user.
3. Add one `.summem/summem note`: the Step 2 owner rule now checks the install record before the Cursor root. It supersedes the round-1 owner-rule note. Follow any nap request the tool prints.
4. Docs under `docs/`: no change. During planning, a grep found no statement of the Step 2 owner rule outside `SKILL.md`, the test module, `systemPatterns.md` and `memory-bank/active/`.

### 4. Verification

1. Run `make ci` from the repo root and read the whole output.
2. Run `claude plugin validate .` and confirm there are no new warnings.
3. The live shim is baked to `~/git/stockroom`, so the pre-commit `make format` sync of this worktree changes nothing outside it. Confirm from `grep '^# STOCKROOM_' ~/.local/bin/stockroom`.

## Technology Validation

No new technology - validation not required. The arm adds `grep -qF --`, which is POSIX; it was checked with GNU grep and BusyBox. The probes and the prototype are recorded under Evidence.

## Dependencies

- `grep` supporting `-q`, `-F` and `--`: GNU, BSD/macOS and BusyBox all do.
- Claude Code's install record. Its fields are documented; the on-disk JSON layout was observed on 2.1.302.
- Claude Code substituting `${CLAUDE_SKILL_DIR}` as `<installPath>/skills/<skill>`, verified live on 2.1.302.

## Challenges & Mitigations

- **The docs describe the record's fields, not its bytes.** Matching the quoted path string does not depend on nesting, key order or indentation. If Claude Code ever stores paths escaped (`\/`), relative, or as `~`, the check misses and the user is asked, as in round 1.
- **JSON escaping.** A path holding `"`, `\` or a control character is stored escaped, and so is a native Windows path (`C:\\…`, while the shell sees `/c/…`). These miss and the user is asked. Default folders on Windows still match by path.
- **An in-place local-marketplace checkout at a cache-shaped path.** The block reads the record next to the checkout's own path, which normally does not exist. Even the real record lists only the cache entry, never the checkout (Evidence). So it cannot give a false `claude`.
- **`--plugin-dir` pointed at a recorded cache copy gives `claude`.** That is correct: the files are the install's, and that install's hooks maintain the shim.
- **Fence selection:** the Step 2 prose must not add a second fence that assigns `SKILL_DIR=`.
- **Seed directories ([`CLAUDE_CODE_PLUGIN_SEED_DIR`](https://code.claude.com/docs/en/plugins/org#seed-containers-and-ci), preflight advisory 2).** Claude Code loads a seed's `cache/<m>/<p>/<v>` copies in place. A seed mounted at the path it was built at has matching record paths and gets `claude`. A seed mounted elsewhere misses, and the agent asks. Both are safe.

## Pre-Mortem

- **The check silently never matches, because the substituted path differs from the recorded string.** The tests write both sides, so they cannot catch this. The live probe settled it on 2.1.302: substitution equals `installPath`, symlink included. Untested: a `CLAUDE_CONFIG_DIR` given with a trailing slash or `..`. The record may keep those, while `pwd` normalizes them. That fails closed, and the cost is round 1's question. Accepted.
- **A later Claude Code moves or renames the record.** The check misses and the user is asked. Accepted, because it fails closed; the SumMem note records the dependency.
- **A reviewer objects to skill text reading a harness's state file.** The file is documented as the install record, and the block only greps it, never writes it. Answer in the PR, not in code.
- **Step 7's new sentence lets an agent skip the checkout question wrongly.** It applies only when the shim's path equals the `APP_DIR` that Step 2 labelled with a harness, which is proof by the same rule. Consent is still asked.

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

- [x] 1. Step 2 install-record check:
    - Red: 8 failed (the 2 layouts, the placeholder case and the quotes case, each under sh and bash), 40 passed.
    - Green: 48 passed, 24 skipped (zsh is absent).
    - Mutation check (`scratchpad/scripts/mutation_check.py`, run on a scratch copy):
        - Unmutated: no failures.
        - Unquoted pattern: only the orphan case fails.
        - No record branch: exactly the 3 recorded tests fail.
    - BusyBox check on the worktree `SKILL.md`: PASS.
- [x] 2. Step 7 sentence, worded per preflight advisory 1: only an owner the block printed, or the user's own answer, lets the agent skip the checkout question. An owner the agent filled in does not.
- [ ] 3. `systemPatterns.md`, brief AC7, SumMem.
- [ ] 4. Verification.

## Preflight advisories: dispositions

- **1 (Step 7 sentence must exclude an owner the agent filled in):** applied in unit 2.
- **2 (seed directories):** added to Challenges below. No code change: a seed mounted at its build path gets `claude`; one mounted elsewhere misses and the agent asks.
- **3 (the match ignores which key holds the string):** accepted. A `projectPath` equal to the copy's path also matches, but that needs a checkout inside Claude Code's own cache folder. "How it fails" is softened to "a copy whose exact path is not a string in the record".
- **4 (custom-root synced copies stay `dev`):** stated under "Who it helps". Synced plugins have no install record; Step 7 still stops and asks.
- **5 (`$`, backtick, `"` or `\` in the skill folder's path breaks `SKILL_DIR="…"`):** exists before this PR and fails closed (no engine found). Logged as a follow-up for Reflect.
- **Radical idea (`${CLAUDE_PLUGIN_DATA}` names the plugin's origin):** not applied. It reverses round 1's premise and contradicts the round-1 probe, so it needs a live probe and an operator decision.
