# Active Context

**Current Task:** p4-dashboard / m1 — Dashboard metrics API server

**Phase:** REFLECT - COMPLETE

## Operator Plan-Review Decisions (2026-07-09)

- `messages.first_seen_at` joins migration `0004` (now `0004_observation_times.sql`): "when stockroom first observed this message", writer-internal carry-forward (carried per `message_id`, else seeded from the session's `source_mtime`), ingest-cadence granularity going forward.
- Doctrine revised in `systemPatterns.md`: the warehouse outlives its sources; rebuild is degraded recovery, not equivalence; never justify a design by future re-ingest of prunable data.
- No `--full` warning needed (it never deletes orphaned rows; carry-forward survives it) — retention contract documented in the ingest docstring instead.

## What Was Done

- Added migration `0004_observation_times.sql` plus cumulative schema contract: `sessions.source_mtime` and `messages.first_seen_at`.
- Extended ingest model/orchestrator/writer so every session receives discovered source mtime, subagents inherit the parent conversation mtime, and message first-observation times survive append, unchanged, and full re-ingest.
- Added `warehouse.open_current()` and `WarehouseStaleError`: missing/current/stale/busy states are typed, the stale path never migrates, and current connections are DuckDB-enforced read-only.
- Added `stockroom.dashboard`: eight per-harness metric endpoints, all-time wrapped rollup, loopback-only threaded HTTP server, static traversal guard, stable JSON refusals, and `python -m stockroom.dashboard` probe/detach/foreground startup.
- Updated the `sr-query` schema map for migration `0004`.
- Added/extended schema, ingest, warehouse, metric, HTTP, CLI, and ingest-to-serve integration tests.
- Corrected partial HTTP bounds so metrics, rather than the transport, retain
  ownership of endpoint-specific defaults; trends now expose 14 calendar days
  and 12 calendar weeks while recent sessions remain open-ended unless bounded.
- Closed the QA coverage and endpoint-documentation gaps, including HTTP
  repeated filters/cap/timeout wiring and stale-schema anti-migration behavior.

## Build Decisions

- Metric output remains client-mode-agnostic; selected unknown harnesses receive zero-valued series rather than an error.
- Deterministic ranking ties use lexical names; wrapped tie-breaks use lexical harness/session and earliest hour.
- `sessions` caps returned rows at 500 defensively in both server and metric layers.

## Deviations

- Updated existing migration-head and warehouse-concurrency expectations from version 3 to 4; this was an expected ripple omitted from the file list, not an architectural change.
- `make format` performs an exact sync and removed the per-machine torch exception. Restored the previously installed `torch==2.13.0+cu126` build and verified the production encoder path.

## Verification

- `make ci`: 402 passed, 3 skipped; ruff lint/format, lock check, and REUSE all passed.
- `stockroom doctor smoke`: CUDA available; production BGE encoder returned a 384-dimensional vector.
- In-process integration: fixture ingest → real warehouse file → `open_current()` → HTTP overview passed.

## Next Step

Run `/niko` to close m1 and continue to the next dashboard milestone.
