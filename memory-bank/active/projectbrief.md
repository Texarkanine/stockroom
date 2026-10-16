# Project Brief

## User Story

As a stockroom user who installs the plugin from a marketplace (Claude Code or Cursor), I want `sr-initialize` and the session-start hooks to find the installed engine and the right shim owner on their own, so that setup does not quietly take the "dev checkout" path and leave me with a wrong-owner shim, or no shim, that later heals badly or not at all.

## Use-Case(s)

### Use-Case 1: Claude Code marketplace install

The user installs `stockroom@txrk9-agent-plugins` with `/plugin` and runs `/stockroom:sr-initialize`, often in the same session, before any SessionStart hook has fired. Step 2 must resolve `OWNER=claude` and `APP_DIR=<plugin root>/skills/sr-search` with no improvising by the agent. Bug report: `.scratch/stockroom-bug-claude-plugin-root-unset.md`.

### Use-Case 2: Cursor marketplace install

The same skill text runs in Cursor. Whatever fix lands for Claude Code must not break, or keep silently breaking, the Cursor path. Cursor's documented behavior for its plugin-root variable must be checked rather than assumed.

### Use-Case 3: Dev checkout / localdev mirror

A contributor runs `sr-initialize` from a repository checkout or a `make localdev` mirror. That path must still resolve to owner `dev` and defer the shim to `make shim`. Nothing may label a marketplace install as a dev checkout.

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
4. The shim ownership policy (`stockroom.shim`) is not changed by this task unless the audit shows it is part of the failure.

## Acceptance Criteria

1. On a Claude Code marketplace install, following `sr-initialize` Step 2 literally gives `OWNER=claude` and the absolute plugin-cache `skills/sr-search` path.
2. On a Cursor marketplace install, Step 2 gives `OWNER=cursor` by a mechanism that is documented or verified, or the remaining uncertainty is stated in the skill or the docs and does not misroute the user.
3. A dev checkout still resolves to `OWNER=dev`.
4. No project doc or comment claims that plugin-root variables are visible to agent-run shell commands.
5. `make ci` (or the equivalent format, lint, test and reuse gates) passes.
