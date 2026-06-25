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
