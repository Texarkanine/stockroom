# Architecture Decision: Dashboard Session-Time Grain (Cursor has no timestamps)

## Requirements & Constraints

The dashboard's panels are almost all time-windowed (30d KPIs with prev-window deltas, 14d daily activity, weekly write/read ratio, recent-sessions table, streak/peak-hour in wrapped). A session therefore needs *some* activity time. The facts, verified empirically against the operator's real data:

- Cursor transcripts carry **no timestamps anywhere** — records are exactly `{role, message.content}` (592 real transcript files scanned; zero time-like keys). `sessions.started_at`/`ended_at` and `messages.ts` are honestly NULL for **all 765 cursor sessions** (vs 39 claude sessions, all timestamped).
- Ingest *already computes* each session file's mtime (`DiscoveredSession.mtime` drives the watermark) — it just doesn't store it per session.
- Every session row carries `source_path` (provenance, NOT NULL).

Ranked quality attributes:

1. **Schema honesty** — one meaning per column, never fabricate a grain we don't have (doctrine in `systemPatterns.md`).
2. **Durability** — metrics are the post-v1 recap substrate; the time grain must live in the warehouse, not depend on ambient filesystem state at request time.
3. **Coverage** — the dominant harness (95% of sessions) must not vanish from the dashboard.
4. **Scope containment** — m1 is the API-server milestone; schema/ingest changes are expansion and must earn their place.

Out of scope: message-grain timestamps for Cursor (unrecoverable — the data does not exist), backfilling wall-clock history we never captured.

## Options Evaluated

- **A — Store the source-file mtime: migration `0004` adds `sessions.source_mtime`, ingest populates it.** New provenance column ("mtime of the session's source transcript file at last ingest"), one uniform meaning for every harness, populated for both. Dashboard computes an activity time as `COALESCE(started_at, source_mtime)` at query time.
- **B — Stat `source_path` at request time.** No schema change; the dashboard stats each session's transcript file per request.
- **C — Exclude Cursor from time-windowed panels.** Render windowed metrics from Claude data only; Cursor appears only in unwindowed panels.
- **D — Overload `ended_at` with the file mtime for Cursor.** Ingest writes mtime into `ended_at` when the harness has no record timestamps.

## Analysis

| Criterion | A: `source_mtime` column | B: request-time stat | C: exclude Cursor | D: overload `ended_at` |
|-----------|--------------------------|----------------------|-------------------|------------------------|
| Schema honesty | Uniform provenance meaning, `source_*` naming convention already exists (`source_path`, `source_uuid`) | No schema impact | Honest but useless | **Violates one-meaning-per-field** — the doctrine names this exact anti-pattern ("`X` is A for Cursor but B for Claude") |
| Durability (recap substrate) | In-warehouse, survives source deletion | **Fragile** — transcripts can be pruned/moved; warehouse is supposed to outlive its sources (faithful-capture raison d'être) | In-warehouse | In-warehouse |
| Coverage | Full (both harnesses) | Full until files vanish | **95% of sessions invisible** | Full |
| Scope | Migration + writer + golden-snapshot update + `--full` re-ingest (all established mechanics: 0002 precedent) | Dashboard-local only | None | Writer change only |
| Risk | Low — forward-only migration, no backfill needed (0002 precedent: re-ingest repopulates) | Medium — silent metric decay as files age out | Product failure | High — permanent semantic rot |

Key insights:

- The mtime is the **only honest time signal Cursor emits**, and it is already flowing through ingest — storing it is capture, not fabrication. Its meaning ("when the source file last changed") is identical for every harness, so it satisfies the doctrine as a *provenance* column even where record timestamps also exist.
- The `COALESCE(started_at, source_mtime)` activity time is a **query-level derivation**, not a stored fabrication — the same shape as the doctrine's approved grain-specific handling (each column keeps one meaning; the dashboard documents its derived "best available activity time").
- B fails the recap-substrate constraint outright: the warehouse exists precisely because harnesses prune their own history.

## Decision

**Selected**: Option A — migration `0004_session_source_mtime.sql` adds `sessions.source_mtime TIMESTAMP`; the ingest writer populates it from `DiscoveredSession.mtime` for every harness.

**Rationale**: The only option that satisfies honesty, durability, and coverage simultaneously. It rides entirely on established mechanics (forward-only migration, structural no-backfill with `--full` re-ingest repopulating, golden-snapshot update as a conscious reviewed diff) and the established `source_*` provenance naming.

**Tradeoff**: m1's scope grows by one thin migration + a writer/orchestrator touch + fixture/golden updates. Accepted: without it the API server cannot serve its spec. Session times for Cursor are last-activity-grained (mtime ≈ session end), so daily-activity buckets date a Cursor session by its *last* write — documented in the endpoint, acceptable for at-a-glance metrics.

## Implementation Notes

- Migration `0004`: `ALTER TABLE sessions ADD COLUMN source_mtime TIMESTAMP;` — comment documents the uniform provenance meaning. `0001`–`0003` snapshots stay frozen; new cumulative `0004_snapshot.json` + `test_schema_0004.py` pin it.
- `NormalizedSession` gains `source_mtime: datetime | None = None`; the orchestrator stamps it from `DiscoveredSession.mtime` (parsers stay pure — they never stat); subagents inherit the parent conversation's mtime (their files aren't separately watermarked).
- Writer inserts the new column; `source_mtime` (machine-dependent) stays out of the golden `expected_rows.json` columns and is asserted dynamically against the fixture file's statted mtime.
- Dashboard queries use `COALESCE(started_at, source_mtime)` as the session activity time; `messages.ts` remains the message-grain time where it exists (Claude-only panels don't exist in v1, so no message-grain workaround is needed).
- Operator's warehouse picks the column up via the normal lazy gate on the next write-path open (nightly ingest / `stockroom migrate`); values fill on the next `--full` re-ingest.

## Amendment: message-grain `first_seen_at` (operator-accepted, 2026-07-09)

Operator review extended the decision: session-grain `source_mtime` alone dates a long-lived session entirely by its *last* activity, and message-grain attribution is **observation-time data that cannot be backfilled** — every ingest that runs without it permanently degrades the future recap's time resolution. Accepted additions:

- **`messages.first_seen_at TIMESTAMP`** joins `0004` (now two columns; the migration is named for observation times, not one column). Uniform meaning for every harness: *"when stockroom first observed this message"* — a claim about the observation process, never about authorship time (Claude rows carry it too; their real `ts` simply dominates it for analytics).
- **Carry-forward in the writer, entirely writer-internal** (parsers and `NormalizedMessage` untouched): `write_session` reads the session's existing `(message_id, first_seen_at)` pairs *before* `_delete_session`, then on insert a message keeps its carried value if its `message_id` pre-existed, else is seeded with the session's `source_mtime`. Seeding from mtime (not wall-clock now) keeps bootstrap honest — pre-existing history retains its real spread instead of collapsing to ingest day — and keeps tests deterministic.
- **Granularity contract:** at ingest cadence (nightly ≈ day grain) going forward; `first_seen_at >= ` the message's true creation time, never older. Known soft spot, accepted: Cursor identity is positional, so a history-*rewriting* (non-appending) harness edit would shift ordinals and misattribute carried times.
- **Retention consequence (doctrine revision, operator-accepted):** `first_seen_at` exists in no source, so the warehouse is no longer fully reconstructable — which was already true in practice (harnesses prune; orphaned rows already persist forever because discovery only touches existing files and delete-then-insert only fires per re-parsed session). Doctrine reframed in `systemPatterns.md`: **rebuild is a degraded recovery path, not an equivalence claim**; no design may depend on future re-ingest of data the harness may prune. `--full` needs no warning — it re-processes existing files only, never deletes orphaned rows, and carry-forward preserves `first_seen_at` through it; the only destructive op is deleting `warehouse.duckdb` itself, which no stockroom command does.
