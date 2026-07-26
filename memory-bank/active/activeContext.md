# Active Context

## Current Task: cursor-vscdb-backfill
**Phase:** PLAN - COMPLETE

## What Was Done
- Probed this machine's live `state.vscdb` (5.7 GB, WSL→Windows mount) to ground the plan: 2,039 composers, 1,131 already in the warehouse, **908 backfill candidates** (609 with resolvable bubbles + 26 legacy-inline, 273 empty drafts), ~75,800 bubbles, 2025-03 → 2026-07.
- Component analysis: new `ingest.cursor_vscdb` parser + new sibling `backfill` orchestrator/CLI; writer, model, paths, warehouse all reused unchanged; the *absence* of an import edge from `ingest`/`schedule` is the "not nightly" guarantee and is asserted by tests.
- Resolved OQ1 (bubble → message reconstruction) via an algorithm creative: keep storable bubbles only; drop thinking-only/empty; tool calls stay on their own bubble-message rather than being merged into the preceding turn.
- Resolved OQ2 (workspace identity) via an architecture creative: `project_id` = native `workspaceId` (CLI-chats precedent), `cwd` from `workspaceStorage/*/workspace.json`, `workspace_key` left to the writer so vscdb sessions converge with same-`cwd` transcript sessions.
- Recorded six evidence-backed plan decisions, two of them measured live: the `mode=ro` → `immutable=1` open ladder (only `immutable=1` works on the mount), and index range bounds instead of `LIKE` (0.05 s vs 2.88 s per composer — this retires the "hybrid prefix/scan" pain from the aborted `enhance-cursor-tokens` work).
- Wrote the full TDD test plan (behaviors, infrastructure, integration, invariant guard tests), a 7-step implementation plan, technology validation, challenges, and a pre-mortem.

## Operator Decisions On Record
- Tokens are **not** a selection gate — tokenless composers are backfilled too (deviation from #84 as written).
- Ponytail applies, but "don't over-cut": production-quality software, no cruft and no code golf.
- **No personal on-disk paths in committed artifacts.** Memory-bank docs, code comments, docs pages, and test fixtures use generic placeholders (`/home/u/p`, `<globalStorage>/state.vscdb`); real machine paths stay in the chat, never in the repo.

## Next Step
- Preflight phase (`niko-preflight` skill) to validate the plan before build.
