# Progress

Deliver milestone m1 of `p4-dashboard`: the dashboard metrics API server — a `stockroom.dashboard` module in the engine package serving the spec's per-harness JSON endpoints (overview, trends, projects, tools, models, efficiency, sessions, wrapped) read-only on port 6767, with repeatable `?harness=` filtering and optional `?since=`/`?until=` windows (spec defaults), a non-migrating open path (typed refusal when the schema is behind), static-file serving, and port-probe idempotent startup. Built test-first; cross-milestone invariants in `memory-bank/active/milestones.md` apply.

**Complexity:** Level 3

## 2026-07-09 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry routed through L4 milestone transition: no sub-run active, m1 is the first unchecked milestone
    - m1 classified via the decision tree: complete feature across multiple components (server module, tests, fixtures), no architectural change — Level 3, matching the milestone list's estimate
    - Sub-run ephemeral state initialized (fresh `progress.md`; `activeContext.md` updated; `projectbrief.md` and `tasks.md` preflight findings preserved for the plan phase)
* Decisions made
    - None new — inherited operator decisions govern: port 6767, windowed endpoints (advisory 5), test-ROI discipline (advisory 6), non-migrating open path (finding 1)
* Insights
    - `tasks.md` findings 1, 5, and 6 are m1-specific inputs the plan phase must fold in: the gate-bypassing read-only open with typed refusal, `?since=`/`?until=` windows, and daemonization living in the CLI with tests limited to our own logic

## 2026-07-09 - CREATIVE (within plan) - COMPLETE

* Work completed
    - Two open questions explored and resolved high-confidence, documented in `memory-bank/active/creative/`
    - Empirical verification against the operator's real data: Cursor transcripts carry zero timestamps (592 files scanned; records are only `{role, message.content}`), so all 765 cursor sessions have NULL `started_at`/`ended_at`/`ts` — the input that forced question 1
* Decisions made
    - **Session time grain:** migration `0004` adds `sessions.source_mtime` (uniform provenance meaning: mtime of the source transcript at last ingest, populated for every harness — ingest already computes it for the watermark); dashboard uses `COALESCE(started_at, source_mtime)` as activity time. Rejected: overloading `ended_at` (one-meaning-per-field violation), request-time stat (recap substrate must survive source pruning), excluding cursor (95% of sessions invisible)
    - **Non-migrating open:** `warehouse.open_current(read_only=True)` chokepoint variant + typed `WarehouseStaleError`; version policy stays in `stockroom.warehouse`, dashboard maps missing/stale/busy to HTTP 503 `{"error", "action"}` (errmsg ratchet)
* Insights
    - The golden ingest snapshot dumps an explicit column list, so `source_mtime` (machine-dependent) simply stays out of the golden — asserted instead by a dynamic stat-comparison test, the same treatment the watermark already gets
