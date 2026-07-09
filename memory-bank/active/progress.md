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

## 2026-07-09 - PLAN - COMPLETE

* Work completed
    - Full L3 plan in `tasks.md`: component analysis (5 components), TDD test plan (~30 behaviors, 4 new test files + 3 extended), 9 ordered implementation steps, challenges/mitigations; L4 preflight findings folded in as a reference section
* Decisions made
    - Server stack: stdlib `http.server.ThreadingHTTPServer` (the roadmap's deferred framework pick) — zero new locked deps, per the spec's KISS directive and the supply-chain posture
    - Per-request `open_current` with a short (~2s) backoff timeout so a nightly-writer lock degrades to a quick busy-503 instead of a 30s hang
    - Metrics scope: non-subagent sessions only (subagent metrics are the spec's noted future Compare-mode addition); model metric at session grain (spec recommendation); write/read tool sets and efficiency buckets as documented tunable constants
    - Windows: `since` inclusive / `until` exclusive; overview prev-period = equal-length interval preceding `since`; wrapped is all-time and ignores the harness selector
    - m1 static serving ships a placeholder `index.html` (PPL-S by existing REUSE layering — lints clean); m2 owns the real front-end and its REUSE carve-outs
* Insights
    - The milestone description implied but didn't name two substrate items now in scope: migration `0004` + ingest population of `source_mtime` — the plan absorbs them at L3 without re-leveling (both ride established mechanics with strong precedents: `0002` structural migration, watermark mtime plumbing)

## 2026-07-09 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - TDD encoding hardened: every implementation step now carries explicit stub → failing-test → implement sub-ordering (was preamble-level)
    - Convention compliance verified: package-with-`__main__` shape (ingest precedent), `main(argv) -> int` dispatcher contract, `NNNN_*.sql` migration naming, con-injection, snapshot discipline, REUSE layering for the placeholder `index.html` — all aligned
    - Dependency sweep: all `INSERT INTO sessions` sites (writer + 4 test sites) use explicit column lists, so `0004` breaks nothing; `migrated_con` picks up `0004` automatically via `apply_pending`; frozen `0001`–`0003` snapshot tests apply only their own chains — unaffected
    - Finding folded: `sr-query` SKILL.md's schema map ("as of 0001–0003") goes stale with `0004` → doc update added to step 9
    - Findings folded from spec re-read: harness enumeration is all-time (idle harness still appears zeroed), `?limit` clamped to 500, server binds 127.0.0.1 only, broad per-request guard so no traceback leaks (clean 500 JSON)
    - `.preflight-status` written: PASS
* Decisions made
    - `metrics.ENDPOINTS` registry (name → callable) as the single routing source shared by server and tests
* Insights
    - Radical-innovation scan produced nothing level-changing; the registry was the one accretive structural improvement worth folding in

## 2026-07-09 - PLAN REVIEW (operator) - COMPLETE

* Work completed
    - Operator reviewed the session-time-grain decision and raised message-grain attribution + the rebuildability doctrine; analysis discussed and recommendation accepted in full
    - Plan amended: `0004` renamed `0004_observation_times.sql` and gains `messages.first_seen_at`; writer carry-forward added to step 2 with three unit behaviors (bootstrap seed, append keeps old + stamps new, unchanged re-write idempotent); creative doc amended; challenges updated
    - `systemPatterns.md` doctrine reframed now (new pattern: "The warehouse outlives its sources — rebuild is degraded recovery, not equivalence" + How-This-Works bullet)
* Decisions made (operator)
    - **`messages.first_seen_at`** ("when stockroom first observed this message" — uniform, all harnesses) joins migration `0004`; writer-internal carry-forward (read pairs before delete; carried if `message_id` pre-existed, else seeded from the session's `source_mtime` so bootstrap keeps history's real spread); granularity = ingest cadence going forward; never older than the message
    - **Doctrine revision:** rebuild is a degraded recovery path, not an equivalence claim; no design may depend on future re-ingest of data the harness may prune; capture-time (observation-derived) data is the most urgent kind — it cannot be backfilled
    - **No `--full` warning:** `--full` re-processes existing files only, never deletes orphaned rows, and carry-forward preserves `first_seen_at` through it; retention contract documented in the ingest docstring instead
* Insights
    - Retention was already structural (discovery touches only existing files; delete-then-insert fires only per re-parsed session; nothing prunes warehouse rows) — the amendment makes the doctrine match the mechanics
    - Accepted soft spot: positional `message_id` means a history-rewriting harness edit would shift ordinals and misattribute carried times; Cursor is append-only in practice and the value stays an honest upper bound

## 2026-07-09 - BUILD - COMPLETE

* Work completed
    - Completed all 9 ordered TDD steps: migration 0004, ingest observation-time plumbing, non-migrating warehouse open, eight dashboard metrics, loopback HTTP/static server, idempotent CLI launcher, documentation, and full verification
    - Added schema, writer/orchestrator, warehouse, metrics, HTTP, CLI, and ingest-to-serve integration coverage
    - Updated the `sr-query` schema map for `source_mtime` and `first_seen_at`
    - Passed `make ci` (396 passed, 3 skipped; lint, format, lock, REUSE green) and the final torch-enabled full suite (398 passed, 1 skipped)
    - Restored the existing per-machine `torch==2.13.0+cu126` build after the Makefile's exact-sync prerequisite removed it; production encoder smoke passed on CUDA
* Decisions made
    - Unknown selected harnesses return zero-valued payload keys, preserving a mode-agnostic non-error API
    - Deterministic ties use lexical ordering; wrapped peak-hour ties choose the earliest hour
    - Sessions responses are capped at 500 in both HTTP validation and the metric function
* Insights
    - The existing `make format`/`make ci` sync prerequisite conflicts with the documented torch-held-out workflow by deleting the per-machine torch install; build restored it immediately, but the Makefile deserves a future inexact-sync correction outside this milestone
    - The migration-head bump required routine updates to existing runner, warehouse snapshot, and concurrency expectations that the plan's file list did not enumerate

## 2026-07-09 - QA - FAIL (FIXABLE)

* Work completed
    - Reviewed all implemented components semantically against the original plan, creative decisions, KISS/DRY/YAGNI, architectural patterns, and explicit test plan
    - Confirmed migration/retention, non-migrating warehouse open, refusal mapping, metric shapes, loopback/static safety, and CLI ownership are structurally aligned
* Decisions made
    - Route back to Build: the HTTP layer must parse only supplied bounds so endpoint-specific defaults remain owned by metrics
    - Treat explicit cross-cutting coverage and Cursor last-activity documentation promised by the plan as completion requirements, not optional QA suggestions
* Insights
    - The universal server-side `default_days=30` expansion is correct for overview/projects/tools/models/efficiency but changes `/api/trends?until=...` from 14d/12w to one 30d window and changes `/api/sessions?until=...` from an open-ended upper bound to an implicit 30d window
    - Core implementation is sound; findings are localized and do not require replanning or creative re-exploration

## 2026-07-09 - BUILD REMEDIATION - COMPLETE

* Work completed
    - Replaced transport-level window expansion with independent ISO-bound parsing; metrics now own all endpoint defaults and validate a pair only when both bounds are supplied
    - Made trends defaults calendar-exact: 14 daily labels and 12 Monday-aligned weekly labels, including when HTTP supplies only `until`
    - Added the QA-requested cross-cutting tests for empty overview shape, default trend lengths, inclusive/exclusive activity edges, subagent exclusion, repeated harness filters, 500-row clamp, short open timeout, stale anti-migration, and missing-warehouse startup
    - Documented Cursor transcript-mtime last-activity semantics on every windowed endpoint and bootstrap NULL-activity behavior on wrapped
* Decisions made
    - A single-bound parser is a public metrics helper because transport parsing must not synthesize an endpoint-specific opposite bound
    - Calendar trend defaults anchor on the last instant included by the exclusive end, avoiding an accidental 15th day or 13th partial week
* Verification
    - Targeted dashboard suite: 27 passed
    - `make ci`: 402 passed, 3 skipped; ruff check/format, lock verification, full pytest suite, and REUSE passed
    - Restored the established out-of-lock `torch==2.13.0+cu126` environment removed by exact sync; CUDA encoder smoke produced a 384-dimensional vector
* Insights
    - Defaults expressed as elapsed durations are not equivalent to fixed calendar bucket counts when labels include both boundary dates; deriving the first bucket from the last included instant keeps API shape stable

## 2026-07-09 - QA REVIEW 2 - COMPLETE (PASS)

* Work completed
    - Re-reviewed the implementation against the original L3 plan, both creative decisions, and the Review 1 findings
    - Confirmed endpoint-specific defaults survive absent and partial HTTP bounds, sessions remain recent-N, and the calendar bucket counts are stable
    - Confirmed all promised cross-cutting contracts now have explicit tests and the activity-time documentation matches the implemented fallback
    - Checked KISS, DRY, YAGNI, completeness, regression, integrity, documentation, and implementation debris; no further findings
* Decisions made
    - QA passes cleanly; the implementation is ready for reflection
* Verification
    - Review used the completed `make ci` result: 402 passed, 3 skipped; lint, format, lock, and REUSE green
    - Production encoder smoke remained green after restoring the established per-machine Torch build
* Insights
    - Keeping transport parsing bound-only is the key ownership boundary: endpoint functions can evolve their defaults without hidden HTTP-layer policy
