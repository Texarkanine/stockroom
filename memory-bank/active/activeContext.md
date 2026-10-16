# Active Context

## Current Task: plugin-root-resolution
**Phase:** PLAN - COMPLETE

## What Was Done
- Intent confirmed by the operator: reassess how `CLAUDE_PLUGIN_ROOT` reaches each plugin surface, then fix `sr-initialize` and the hook configuration where they set users up to fail.
- Verified the model against the Claude Code docs, a headless probe on 2.1.301, Cursor forum and staff statements, and warehouse history. The details are in `tasks.md` under "Evidence that shaped the plan".
- Plan: rewrite `sr-initialize` Step 2 (sibling `APP_DIR`, then a 5-rule owner resolution) and Step 7 (always a guarded install). Make two doc fixes. Add `skills/sr-search/tests/test_initialize_context.py`. Hooks are unchanged because the audit found them correct.

## Next Step
- Preflight (subagent), then Build.
