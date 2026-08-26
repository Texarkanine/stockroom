# Active Context

## Current Task: dashboard-md-backslash-escape
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Root cause: CommonMark `escape` on session-body markdown-it. Stored `\.cursor` is intact.
- Fix: `bindSessionMarkdown` calls `markdown.disable("escape")` and is the dashboard's session render binding. No ingest/warehouse change. No shim or live-dashboard restart.
- Tests: new JS case on the vendored markdown-it; full worktree `make test` green.

## Next Step
- L1 wrap-up: persistent files skipped; completion commit. Live :58008 still deferred.
