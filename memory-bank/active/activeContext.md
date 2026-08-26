# Active Context

## Current Task: cursor-model-ingest
**Phase:** PLAN - COMPLETE

## What Was Done
- Diagnosed the Aug 20 Cursor model cutoff: not a schema change. `_wsl_windows_candidate_paths` aborts the whole `/mnt` walk when a stale drive letter raises `OSError` (`/mnt/i` → `ENXIO` on this machine), so ingest never merges `/mnt/s/Users/Austin/.cursor/ai-tracking/ai-code-tracking.db`. That DB still uses `ai_code_hashes.conversationId` + `model` and is current. Linux `~/.cursor/ai-tracking/ai-code-tracking.db` is stale (last write 2026-08-08).
- Planned a fail-soft per-entry `/mnt` walk; leave the SQL reader unchanged; one `--full` ingest after the fix to refill already-written NULL `models`.

## Next Step
- Preflight validation
