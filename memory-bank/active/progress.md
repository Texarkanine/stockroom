# Progress

Milestone 2 of the `p1-data-backbone` L4 project: **Migration framework**. Build the numbered, one-per-file, forward-only SQL migration subsystem inside the `sr-search` skill: a `schema_version` record, a lazy version gate (each consumer checks the schema version before touching the DB), forward-only application under an exclusive write lock, concurrency-safe reader degradation, and the harness-neutral warehouse-open/connection helper. The milestone-1 schema (`0001_initial_schema.sql`) ships as migration `0001` — wrapped in place, no file move. The lock primitive and reader wait/backoff semantics are chosen here. Authored test-first against real and pathological scenarios, preserving the L4 cross-milestone invariants (no truncation, harness-labeled single schema, forward-only migrations, harness-neutral `~/.stockroom/` warehouse home, locked-uv trust, green `make ci` gate).

**Complexity:** Level 3

## 2026-06-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project. Milestone 1 (Schema field enumeration + locked DDL) was `REFLECT - COMPLETE`; checked it off in `milestones.md` and cleared its sub-run ephemeral files (Step 2a).
    - Classified the next unchecked milestone (Migration framework) as **Level 3**, matching the L4 plan/preflight advisory estimate.
    - Created fresh sub-run ephemeral files (this `progress.md`, stubbed `tasks.md`, refreshed `activeContext.md`); preserved the L4 `projectbrief.md`, `milestones.md`, and milestone-1 `reflection/`.
* Decisions made
    - L3, not L4: a complete feature across multiple cooperating components (migration runner, `schema_version` record, lazy gate, exclusive write lock, reader degradation, connection helper), but the overarching architecture is already fixed by the L4 plan — this sub-run delivers one cohesive subsystem, not new architecture.
* Insights
    - The milestone description carries an explicit preflight directive: confirm the migration-system shape stays single-sub-run scoped (it trends toward L4). Surface this in PLAN and resolve it at PREFLIGHT before BUILD.

## 2026-06-25 - PLAN - OPEN QUESTIONS (handing to CREATIVE)

* Work completed
    - Read the authoritative design (tech-brief Migrations + Storage/Concurrency + Open Build-Time Questions; roadmap Phase 1) and surveyed the engine (`migrations/0001`, conftest `schema_con`, pyproject, Makefile, package layout).
    - Ran a planning POC of DuckDB 1.5.4 cross-process locking: a RW connection takes an **exclusive** OS file lock (excludes all other-process opens, RW *and* RO, with `IOException: Could not set lock`); a RO connection takes a **shared** lock (excludes a RW). Pinned the model + a state diagram in `tasks.md`.
    - Wrote component analysis to `tasks.md`: new `stockroom.warehouse` open helper (single chokepoint), migration runner + lazy gate, `migrations/` discovery, lock primitive, reader-degradation helper; mapped dependencies, boundary changes, and the invariants the build must preserve.
    - Identified three open questions; Q1 (lock primitive) + Q2 (reader wait/backoff semantics) are genuine concurrency-architecture ambiguity the tech-brief explicitly defers to build → invoking the architecture creative phase. Q3 (`schema_version` bootstrap placement) is lower-ambiguity, likely resolved in-plan.
* Decisions made
    - The warehouse-open helper is the single contract every consumer goes through; the lazy gate lives inside it so no consumer can touch an un-migrated DB.
    - Strong preference for a **stdlib-only** lock primitive so `uv.lock` stays untouched (locked-uv trust).
* Insights
    - DuckDB already guarantees migration exclusivity via its own RW file lock; the framework's real work is coordinating would-be migrators (anti-thrash), making the writer wait for readers to drain, and translating the raw open-time `IOException` into bounded, graceful reader backoff. That correctness-under-parallel-access surface is exactly what the tech-brief says must be *tested*.

## 2026-06-25 - CREATIVE (warehouse concurrency & migration-lock) - COMPLETE (high confidence)

* Work completed
    - Ran the architecture creative phase on the coupled Q1/Q2 concurrency question; wrote `creative/creative-warehouse-concurrency-locking.md` (requirements, 3 options, comparison table, decision, implementation notes).
    - POC-verified `fcntl.flock` on WSL-internal ext4: `LOCK_EX`/`LOCK_NB` semantics and **auto-release on process death** (parent acquired 1.52s in after the holder exited without unlocking). Confirmed `HOME` is `/home/mobaxterm` (not a `/mnt` mount), so the lockfile dodges the Windows-mount `flock` hazard.
* Decisions made (high confidence)
    - **Q1:** `fcntl.flock(LOCK_EX)` sidecar lock = single-writer/migrator token; readers never take it. In-DB lock rejected as structurally circular; DuckDB-lock-only rejected as herd-prone.
    - **Q2:** bounded exponential backoff + jitter catching DuckDB's open-time `IOException`; typed `WarehouseBusyError` on timeout; writers use the same backoff to wait for readers to drain; double-checked lazy gate.
    - **Q3 (consequence):** `schema_version` is a runner-owned `CREATE TABLE IF NOT EXISTS` bootstrap table, not in `0001` — keeps the locked `0001` contract + golden snapshot intact.
* Insights
    - The right external lock complements DuckDB's guarantee instead of duplicating it: DuckDB gives data integrity (RW exclusive), flock gives orderly, herd-free, crash-safe *coordination* of would-be writers. An in-DB advisory lock can't do this because acquiring it already requires the exclusive RW connection it would be guarding.

## 2026-06-25 - PLAN - COMPLETE

* Work completed
    - Finalized the L3 plan in `tasks.md`: proposed module layout (`migrations/` discovery, `migrate.py` runner, `warehouse.py` chokepoint), full TDD test plan (discovery, runner, warehouse-open, lock primitive, and a multi-process concurrency suite), 9 ordered implementation cycles, technology validation, and challenges/mitigations.
    - Marked all plan status boxes complete except Preflight/Build/QA; updated `activeContext.md`.
* Decisions made (in-plan, no further creative needed)
    - Module split: discovery in `migrations/__init__.py`; runner in `migrate.py`; open/flock/backoff chokepoint in `warehouse.py`. Lazy gate lives inside `warehouse.open()` so no consumer can reach an un-migrated DB (and the future hook simply never calls it).
    - No new dependency — `fcntl`/`os` stdlib + locked duckdb; `make lock-check` guards `uv.lock`.
    - Concurrency tests assert on outcomes (final version, typed error, no double-apply) with injectable timeouts/backoff to avoid timing flakiness.
* Insights
    - The only genuine ambiguity was the concurrency design (now resolved); the rest of the milestone is standard forward-only-migration machinery. Confident it stays L3 (one cohesive subsystem, no independent workstreams) — to be confirmed at preflight per the milestone's L4-creep flag.

## 2026-06-25 - PREFLIGHT - PASS (with advisories)

* Work completed
    - Validated the plan against codebase reality (TDD encoding, conventions, dependency impact, conflicts, completeness). Wrote `.preflight-status`.
    - Confirmed REUSE is path-based (`REUSE.toml` lines 28-37 re-assert AGPL on `skills/**/*.py` + `tests/**`) → no inline SPDX headers for new modules/tests. Grep confirmed no pre-existing connection/migration/flock code (no conflict/duplication).
    - **L4-creep check (milestone directive): PASS** — one cohesive subsystem (single `open()` chokepoint + runner + discovery + tests), no independent workstreams; stays Level 3, single sub-run.
* Amendments made to `tasks.md`
    - Hardened per-step TDD ordering: each of the 9 steps now carries explicit RED (write+fail named test) before GREEN (implement) — same fix class as m1's preflight.
    - **Radical-innovation (in-scope, applied):** added a migrated-schema-equals-snapshot test (step 8) — a fresh `warehouse.open()` must yield a product-table schema byte-matching m1's `0001_snapshot.json`, reusing m1's introspection helper. Ties the framework to the locked DDL.
* Advisories (non-blocking)
    - `STOCKROOM_HOME` is a new env convention later milestones (m3/m4/dashboard) will adopt; chosen now, documented for visibility.
    - A durable "two-layer warehouse lock" `systemPatterns.md` entry deferred to reflect.
* Next
    - 🧑‍💻 Operator-gated **Build** (`/niko-build`). Preflight PASS → Build requires operator initiation per the L3 workflow.

## 2026-06-25 - BUILD - COMPLETE

* Work completed
    - Built the forward-only migration subsystem test-first through all 10 ordered plan steps (0–9), committing per step (RED→GREEN each).
    - Step 0: convention sweep — removed `from __future__ import annotations` from the existing 8 engine/test files (pure refactor, suite green).
    - `stockroom.migrations`: `Migration` NamedTuple, `migrations_dir()`, `discover()` (ascending `NNNN_*.sql`, numeric ordering, non-conforming names ignored).
    - `stockroom.migrate`: runner-owned `schema_version` bootstrap table, `current_version()` (0 pre-bootstrap), forward-only `apply_pending()` (per-migration transaction wrapping DDL + bookkeeping insert → atomic rollback; idempotent; no-op when current/ahead).
    - `stockroom.warehouse`: the single `open()` chokepoint — harness-neutral home (`STOCKROOM_HOME`-overridable, auto-created), `_flock` single-writer/migrator token, `_open_with_backoff` (bounded exp backoff + jitter → typed `WarehouseBusyError`; non-lock IOExceptions propagate), double-checked lazy gate (reader can become migrator; writer holds flock for the connection lifetime).
    - Multi-process concurrency suite (`subprocess` workers): reader degradation (busy→`WarehouseBusyError`; succeeds after release), writer drain (typed error on short timeout), racing-migrator serialization (both reach v1, one bookkeeping row, schema intact). Validated the built chokepoint with no production changes.
    - Radical-innovation guard: a freshly opened warehouse's product schema byte-matches m1's `0001_snapshot.json` (excluding runner-owned `schema_version`). Repointed `techContext.md` Warehouse Schema note at the real modules + two-layer lock.
* Decisions made (build-time)
    - **Writer flock lifetime via `weakref.finalize`**: `duckdb` connections reject `setattr` (C type, no `__dict__`) but support weakrefs, so the writer flock releases when the connection object is finalized — honoring the creative doc's "flock held for the connection's lifetime" without a wrapper type. No architectural deviation.
* Verification
    - `make ci` green: sync, `lock --locked` (uv.lock **untouched** — stdlib `fcntl`/`os`, no new dependency), ruff lint + format-check clean, **89 tests passed** (26 new for m2), REUSE compliant (122/122). Concurrency suite stable across repeated runs.
* Insights
    - The concurrency tests needed zero production fixes — the units (flock + DuckDB native lock + backoff) composed exactly as the creative phase predicted. DuckDB's transactional DDL made `apply_pending` atomicity a clean property to assert (the failing-migration rollback "just works").

## 2026-06-25 - QA - PASS

* Work completed
    - Semantic review of the built subsystem against the plan + creative doc across KISS/DRY/YAGNI/Completeness/Regression/Integrity/Documentation. Wrote `.qa-validation-status`.
    - Applied three trivial fixes (no substantive/blocking findings): (1) removed stale "(added in a later build step)" parentheticals from `warehouse.py`'s module docstring now that flock + backoff exist; (2) refactored `_migrate_under_lock` to reuse the `_flock` context manager instead of hand-rolling `os.open`+`flock`+release (DRY — `_flock` is now production-used, not test-only); (3) added `test_open_with_migrate_false_skips_the_gate` to cover the planned-but-untested `migrate=False` public branch.
* Decisions made
    - Kept `migrate=False` (it is in the plan's `open()` signature) and closed its coverage gap rather than pruning it.
    - Left small test-local `_table_names`/`_PRODUCT_TABLES` repetition intentionally (keeps each test file standalone; not worth the coupling).
* Verification
    - `make ci` green: sync, `lock --locked` (uv.lock untouched), ruff lint + format-check clean, **90 tests passed**, REUSE compliant (122/122).
* Insights
    - The only debris from an incremental, step-numbered build was *documentation* drift (a docstring written for a future step) and a helper that landed before its production caller. Both are characteristic QA catches that lint/test can't see.
