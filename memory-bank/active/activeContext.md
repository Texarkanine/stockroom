# Active Context

## Current Task: cursor-vscdb-backfill (rework — ADHD docs)
**Phase:** BUILD - COMPLETE

## What Was Done
- Link hygiene across `docs/` (nest fallout); strict docs build green as baseline.
- ADHD rewrites of `docs/user-guide/ingest/index.md`, `backfill/index.md`, `backfill/cursor-vscdb.md`.
- B1–B8 checklist + `make docs-build --strict` green.

## Files modified
- `docs/user-guide/ingest/index.md`
- `docs/user-guide/ingest/backfill/index.md`
- `docs/user-guide/ingest/backfill/cursor-vscdb.md`
- `docs/architecture/{backfill,lifecycle,embeddings,warehouse}.md`
- `docs/contributing/{backfill-adapters,iteration}.md`
- `docs/user-guide/{index,dashboard,search,skills,installed-layout}.md`
- `docs/user-guide/troubleshooting/index.md`

## Key decisions
- ProperDocs strict mode requires explicit `index.md` in directory links (trailing `/` rejected).
- Embed is step 4 inside Required Sequence (not a later section).
- How It Reads keeps the silent-miss consequence; SQLite ladder detail stays on architecture.

## Next Step
- QA (automatic per Level 2 workflow).
