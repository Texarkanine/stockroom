# Active Context

## Current Task: Surgical embedding invalidation (#43)
**Phase:** BUILD - COMPLETE

## What Was Done
- Replaced blanket cascade with compare-and-keep in `write_session`
- Added `_embedding_owner_ids_to_invalidate`; removed embedding DELETE from `_delete_session`
- Replaced cascade test with 7 surgical contract tests
- Updated `system-model.md` and `docs/architecture/embeddings.md` staleness wording
- Verification: 530 passed, 3 skipped; ruff format/lint clean

## Files modified
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/ingest/writer.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_ingest_writer.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/references/system-model.md`
- `/home/mobaxterm/git/stockroom/docs/architecture/embeddings.md`

## Key decisions
- Surgical delete via `UNNEST(?::VARCHAR[])` of stale owner ids before `_delete_session`
- Pure helper for text-compare rules (unit-tested)

## Deviations from Plan
- None - built to plan

## Next Step
- QA review (automatic per Level 2 workflow)
