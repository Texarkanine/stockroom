# Active Context

## Current Task: claude-token-overcount
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- Confirmed the overcount, then attributed each Claude API response's token counts once. Lines that share `message.id` and `requestId` keep the field-wise max on the last line; the other lines in the group store NULL. Text and tool calls stay on their own rows.
- A subagent row that repeats its parent's `(api_message_id, request_id)` has its token columns cleared at ingest. Those two fields are parse-time only; the writer does not persist them.
- Documented the count in the warehouse architecture page and documented `stockroom ingest --full` as the way to rewrite sessions whose transcripts are still on disk. Sessions whose transcripts are gone are left as stored.

## Files
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/ingest/claude.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/ingest/model.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/ingest/__init__.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_ingest_claude.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_ingest_orchestrator.py`
- `/home/mobaxterm/git/stockroom/docs/architecture/warehouse.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/load/basic.md`

## Decisions
- No schema migration and no warehouse UPDATE for transcripts that are gone.
- Field-wise max, not "keep the last line's usage".

## Deviations
- This machine's uv 0.8.22 fails `test_docs_lock_is_not_stale` and `make lock-check` on the committed root lock. That failure is independent of this change. Engine pytest otherwise passed (888 passed, 4 skipped). Dashboard JS tests passed (134). Lint, format check, schema-docs check, and reuse lint passed.

## Next Step
- QA review.
