# Active Context

**Current Task:** p4-dashboard / m1 — Dashboard metrics API server

**Phase:** BUILD - IN-PROGRESS (preflight PASS; implementing the validated nine-step TDD plan)

## Operator Plan-Review Decisions (2026-07-09)

- `messages.first_seen_at` joins migration `0004` (now `0004_observation_times.sql`): "when stockroom first observed this message", writer-internal carry-forward (carried per `message_id`, else seeded from the session's `source_mtime`), ingest-cadence granularity going forward.
- Doctrine revised in `systemPatterns.md`: the warehouse outlives its sources; rebuild is degraded recovery, not equivalence; never justify a design by future re-ingest of prunable data.
- No `--full` warning needed (it never deletes orphaned rows; carry-forward survives it) — retention contract documented in the ingest docstring instead.

## What Was Done

- Full L3 plan written to `tasks.md`: component analysis, resolved open questions, TDD test plan, 9 ordered implementation steps, challenges/mitigations.
- Two open questions resolved via creative phase (both high-confidence): `sessions.source_mtime` via migration `0004` as the honest session-time grain for Cursor (`COALESCE(started_at, source_mtime)` activity time), and `warehouse.open_current()` + `WarehouseStaleError` as the non-migrating open path with HTTP 503 `{"error", "action"}` refusals.
- Plan-level decisions: stdlib `http.server.ThreadingHTTPServer` (the roadmap's deferred framework pick — no new locked deps), per-request short-timeout opens, session-grain model metric, tunable write/read tool sets and efficiency buckets, subagent sessions excluded from v1 metrics, wrapped ignores the harness selector.
- Scope grew by two substrate items the milestone description implied but didn't name: migration `0004` + ingest population of `source_mtime` (still comfortably L3).

## Next Step

Execute step 9: schema-map documentation, full-suite CI, and final build handoff.
