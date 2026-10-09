# Active Context

## Current Task: claude-token-overcount
**Phase:** BUILD - IN PROGRESS

## What Was Done
- Confirmed the overcount in code: `_build_message` copies `message.usage` onto every kept assistant line, and `session_token_usage` sums those columns. Committed fixtures put one content array on one line, so current tests do not catch a split response.
- Planned a Level 2 fix: keep one row per line; attribute the field-wise max once per `(message.id, requestId)` inside the session; clear token columns on a subagent row that repeats its parent's response id. The view and dashboard stay as they are.
- On-disk sessions are corrected by the existing `ingest --full` delete-then-insert path. Vanished transcripts are not rewritten: the rows lack API identity, and the consecutive-triple collapse is not exact.
- Completed preflight validation of the plan (PASS WITH ADVISORY). Verified TDD ordering across executable units, DuckDB view compatibility, and fixture isolation.

## Next Step
- Step 1 is green: one token attribution per Claude API response. Step 2 drops forked parent copies on subagents.

