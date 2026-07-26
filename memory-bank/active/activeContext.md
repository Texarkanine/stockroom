# Active Context

## Current Task: cursor-vscdb-backfill (rework — architecture atlas)
**Phase:** BUILD - COMPLETE

## What Was Done
- Edited `docs/architecture/backfill.md`: Invariants block; tightened skip-set and `source_mtime`/`first_seen_at` paragraphs; named keep-predicate → embed invalidation under `--force` with link to `#fixing-a-run`
- One-line fallout fix: restored `Cursor` on `#### Cursor \`sessions.models\` Enrichment` in `docs/user-guide/ingest/index.md` so installed-layout anchor resolves (pre-existing from prior ADHD demotion)
- `make docs-build` strict green

## Next Step
- QA review (autonomous per Level 2 workflow)
