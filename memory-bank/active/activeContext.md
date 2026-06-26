# Active Context

## Current Task: Trace ingest (ETL) (milestone 3 of `p1-data-backbone`, Level 3 sub-run)

**Phase:** BUILD - COMPLETE (all 11 steps; `make ci` green)

## What Was Done

- **BUILD:** implemented the whole `stockroom.ingest` package TDD, one RED→GREEN commit per step (1-11). Modules: `model` (harness-neutral dataclasses), clean-room parsers `cursor`/`claude`, `sources` (discovery + decode + watermark), `enrich` (optional `ai-code-tracking.db`, graceful no-op), `writer` (delete-then-insert + watermark upsert), `ingest()` orchestrator, and the `python -m stockroom.ingest` CLI. Reconstruction is locked by a byte-for-byte golden snapshot (`tests/fixtures/ingest/expected_rows.json`). Docs reconciled in `techContext.md`. Final gate: `make ci` = 152 passed, ruff clean, REUSE compliant.
- Carried the durable clean-room-parser/golden-snapshot pattern entry to REFLECT (per preflight advisory).

## What Was Done (plan/preflight)

- Advanced the L4 project past milestone 2; classified milestone 3 (Trace ingest / ETL) as **Level 3** (Step 2a + complexity analysis).
- **PLAN:** wrote the full L3 plan to `tasks.md` — component analysis (new `stockroom.ingest` package: `model`/`cursor`/`claude`/`sources`/`enrich`/`writer`/orchestrator/CLI), the source→schema mapping, the identity/reconstruction algorithm, a TDD test plan, a 11-step ordered implementation plan, and challenges.
- **Empirical de-risking:** ran structural-only probes of the operator's real Cursor + Claude logs. Findings that shaped the plan: (1) Claude `parentUuid` chains genuinely **branch** (→ parent reconstruction must use the uuid tree to nearest-kept ancestor, not positional); (2) real Claude logs carry **many more record types** than the committed fixtures (→ allowlist-driven parsing + fixture extension); (3) Claude subagent records carry the **parent's** `sessionId` (→ subagent `session_id` from file stem/`agentId`). `ai-code-tracking.db` is **absent** on this machine (→ enrichment is a tested graceful no-op).

## Key Decisions (in-plan, no creative needed)

- Dense ordinals over kept messages; Cursor parent = previous-kept, Claude parent = `parentUuid`-tree → nearest-kept ancestor.
- Idempotent re-ingest via delete-then-insert per `(harness, session_id)`; mtime watermark per `(harness, source_root)`; `--full` bypass.
- No schema change / no new migration; no new runtime dependency (stdlib `json`/`sqlite3` + locked `duckdb`). New env conventions `STOCKROOM_CURSOR_ROOT`/`STOCKROOM_CLAUDE_ROOT`.

## Next Step

- BUILD → QA is autonomous. Run `/niko-qa` for the post-implementation semantic review (Level 3 gate before REFLECT).
