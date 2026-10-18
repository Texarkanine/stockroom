# Project Brief

## User Story

As a stockroom user who installs the plugin from a marketplace (Claude Code or Cursor), I want `sr-initialize` and the session-start hooks to find the installed engine and the right shim owner on their own, so that setup does not quietly take the "dev checkout" path and leave me with a wrong-owner shim, or no shim, that later heals badly or not at all.

## Use-Case(s)

### Use-Case 1: Claude Code marketplace install

The user installs `stockroom@txrk9-agent-plugins` with `/plugin` and runs `/stockroom:sr-initialize`, often in the same session, before any SessionStart hook has fired. Step 2 must resolve `OWNER=claude` and `APP_DIR=<plugin root>/skills/sr-search` with no improvising by the agent. Bug report: `.scratch/stockroom-bug-claude-plugin-root-unset.md`.

### Use-Case 2: Cursor marketplace install

The same skill text runs in Cursor. Whatever fix lands for Claude Code must not break, or keep silently breaking, the Cursor path. Cursor's documented behavior for its plugin-root variable must be checked rather than assumed.

### Use-Case 3: Dev checkout / localdev mirror

Contributors always get `dev` (operator decision). Anything run from a checkout with intent to develop or iterate resolves to `dev` and points to `make localdev` / `make shim`. That covers `claude --plugin-dir`, Cursor `plugins/local`, local-path marketplaces loaded in place, and the Cursor localdev mirror. In Claude Code it also covers a `--plugin-dir` checkout at a cache-shaped path: Claude Code's substituted data folder (`stockroom-inline`) identifies it. Only a checkout inside the active plugins root's own `cache/` folder, where Claude Code keeps installed copies, counts as an install. Only a marketplace install, a harness cache copy at `…/cache/<marketplace>/<plugin>/<version>`, is a real install. A contributor's live `dev` shim is left alone. Nothing may label a marketplace install as a dev checkout.

### Use-Case 4: Leaving dev without getting stuck

A contributor who has a real install and a `dev` shim goes back to the release. Either they run `make localdev-clean`, or they simply delete the checkout or worktree. The next session of the installed plugin restores a working shim in both cases, because a dead shim of any owner is replaced. A contributor who edits the hook code itself is on their own.

## Requirements

1. Rebuild the project's model of where `CLAUDE_PLUGIN_ROOT` reaches, from the official Claude Code docs: hook commands (substituted inline and exported), MCP/LSP servers, skill bodies (braced `${...}` substituted inline at load), and the Bash tool (never present).
2. Do the same for `CURSOR_PLUGIN_ROOT` in Cursor (hooks, skill content, agent terminal), as far as docs and evidence allow. Record what stays unknown.
3. Fix `sr-initialize` context detection and engine-dir resolution so that each harness's marketplace install resolves its own owner and engine dir by a documented mechanism.
4. Audit `hooks/claude-hooks.json` and `hooks/cursor-hooks.json` against that model. Change them only where the model shows a real fault, such as quoting or an unset variable.
5. Correct project docs, code comments and memory-bank text that state the wrong model.
6. Tests pin the detection contract, so that a regression to a Bash-environment read fails CI.

## Constraints

1. Shared `skills/` tree: one `SKILL.md` serves both harnesses. Committed layout is install layout, with no build step.
2. The session-start hook stays idempotent, fire-and-forget and never-erroring.
3. TDD per `.claude/rules/shared/always-tdd.md`: test product behavior and published contracts, not prose change-detectors.
4. The shim ownership policy (`stockroom.shim`) changes in one approved way: `rectify` replaces a dead shim of any owner. A live foreign shim and any unidentifiable file stay untouched. Hook files and dev-load hook behavior stay as they are (operator decision).
5. No separate dev data: dev runs checkout code against the real warehouse after a backup (operator decision).

## Acceptance Criteria

1. On a Claude Code marketplace install in the default plugins folder (`~/.claude/plugins/…`), following `sr-initialize` Step 2 literally gives `OWNER=claude` and the absolute plugin-cache `skills/sr-search` path. Under a custom plugins folder, AC7 applies.
2. On a Cursor marketplace install, Step 2 gives `OWNER=cursor` by a mechanism that is documented or verified, or the remaining uncertainty is stated in the skill or the docs and does not misroute the user.
3. Every checkout-based load (`claude --plugin-dir`, Cursor `plugins/local`, local-path marketplace in place, Cursor mirror) resolves to `OWNER=dev`. That includes a Claude Code `--plugin-dir` checkout three levels below a folder named `cache`, once Claude Code substitutes its data folder (`stockroom-inline`). The exceptions:
    - A checkout inside the active plugins root's own `cache/` folder, where Claude Code keeps installed copies, gets `claude`.
    - When no data folder is substituted, a cache-shaped checkout outside the default plugins folders gets no owner, and in Claude Code the user decides (AC7).
    - In Cursor the agent names `cursor` (accepted residual).

    Re-running `sr-initialize` never offers to take over a shim that its owner still maintains.
4. A `dev` shim whose checkout is gone is replaced at the next session start of an installed stockroom plugin. A live foreign shim is never touched.
5. No project doc or comment claims that plugin-root variables are visible to agent-run shell commands.
6. `make ci` (or the equivalent format, lint, test and reuse gates) passes.

### Added by the PR #142 review (2026-10-16)

7. In Claude Code, no checkout is labelled `claude` because of where its path happens to sit. The path labels a copy only inside a harness's default plugins folder (`…/.claude/plugins/cache/…`, `…/.claude/plugins/synced/…` or `…/.cursor/plugins/cache/…`). Outside those folders, Claude Code's substituted plugin root is not proof, but its plugin data folder and its install record are:
    - A copy gets `claude`, with no question, when the data folder Claude Code substitutes (`data/<plugin-id>`) sits in the plugins root that holds the copy's `cache/`, or when `installed_plugins.json` there lists its exact path.
    - It gets `dev` when the data folder is `stockroom-inline` (a `--plugin-dir` load).
    - Otherwise the agent asks the user.

    Cursor users get no new question: Cursor keeps its first-pass outcomes (operator decision).
8. The line Step 2 prints is valid shell for any path the block resolves that contains no newline, including paths that contain `'` or spaces.
9. `shim rectify` exits 0 and leaves the shim untouched when a foreign shim's engine directory cannot be checked. `shim install` refuses such a shim unless both `--takeover` and `--force` are passed. Neither command raises an exception.

### Added by rework round 3 (operator decision, 2026-10-17)

10. When Claude Code's substituted data folder is missing, renamed or moved, Step 2 falls back to the install record and then to the question. Any such failure shows up during `sr-initialize`, as the question plus an error line that names the data folder, when one was given. It never produces a wrong owner, so nothing new reaches the session hooks, `shim rectify` or the nightly job.

### Added by rework round 4 (operator decision, 2026-10-18)

11. Paths that contain a space or `'` work everywhere stockroom writes them into shell text:
    - the Step 2 block, Steps 3 to 7, the shim and both hooks (already true);
    - the nightly cron and launchd entries;
    - the Makefile's `shim`, `torch`, `local-engine` and `local-dashboard` targets;
    - `localdev.sh`'s printed hint;
    - `stockroom doctor smoke`'s printed torch command, which `sr-initialize` has the agent run.

    Other shell characters (`$`, a backtick, `"`, `\`, `%`) are out of scope.
12. The nightly job runs against the stockroom home it was installed for. `schedule status` reports an installed entry that differs from the current rendering, and which home it carries. `sr-initialize` then offers to re-install it, with the user's consent.
