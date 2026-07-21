# Active Context

## Current Task: cursor-cli-and-entrypoint-ingest
**Phase:** BUILD - COMPLETE

## What Was Done
- Migration `0008_entrypoint.sql` + golden schema; model/writer persist `entrypoint`
- Claude passthrough; Cursor IDE stamps `ide`; new `cursor_chats` parser (root-hash walk) stamps `cli`
- Dual Cursor roots with independent watermarks; collision prefers `store.db`
- Docs: ingest.md, warehouse.md, sr-query SKILL; techContext env var
- Verification: 648 passed / 4 skipped (pytest); 92 JS tests passed

## Files Created or Modified
- `migrations/0008_entrypoint.sql`, `tests/test_schema_0008.py`, `fixtures/schema/0008_snapshot.json`
- `ingest/model.py`, `writer.py`, `claude.py`, `cursor.py`, `cursor_chats.py` (new), `sources.py`, `ingest/__init__.py`
- Tests: writer/claude/cursor/cursor_chats/sources/orchestrator + warehouse head pins → 8
- Fixtures: synthetic `cursor_chats/.../store.db`, updated `expected_rows.json`
- Docs: `docs/user-guide/ingest.md`, `docs/architecture/warehouse.md`, `skills/sr-query/SKILL.md`

## Key Implementation Decisions
- Collision set = all discovered chat ids (not only selected), so incremental runs don't re-admit transcripts
- CLI `cwd` from Workspace Path kept when present; `project_id` remains chats hash dir
- Roundtrip `encode_for` invariant exempts `entrypoint='cli'`
- Corpus fixtures pin empty chats root so golden stays agent-transcripts-focused

## Deviations from Plan
- Bumped `_HEAD_VERSION` / migrate-runner / warehouse locked snapshot to 0008 (required by existing head-pin tests; not listed as its own plan step)
- No other plan drift

## Integration Test Results
- Orchestrator: collision, non-collision, dual watermarks, Claude desktop round-trip, corpus `ide` stamp — all pass
- Full suite green after head-version bump

## Next Step
- QA review (`/niko-qa` or automatic Level 3 transition)
