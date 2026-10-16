# Active Context

## Current Task: plugin-root-resolution
**Phase:** PLAN - COMPLETE (revised after preflight FAIL (fixable))

## What Was Done
- Intent confirmed by the operator: reassess how `CLAUDE_PLUGIN_ROOT` reaches each plugin surface, then fix `sr-initialize` and the hook configuration where they set users up to fail.
- Verified the model against the Claude Code docs, a headless probe on 2.1.301, Cursor forum and staff statements, and warehouse history. The details are in `tasks.md` under "Evidence that shaped the plan".
- Plan revised for preflight: the mirror test expects the logical path, Step 7 sorts shims by header owner and baked dir, and a plugin root counts only when it holds this engine. Tests run under sh, bash and zsh.
- Decision A2 (agent-made, flagged for the operator): `claude --plugin-dir <checkout>` resolves to `claude`, matching that session's own SessionStart hook.

## Next Step
- Preflight again (subagent), then Build.
