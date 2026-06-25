---
task_id: p1-data-backbone-m2-migration-framework
date: 2026-06-25
complexity_level: 3
---

# Reflection: Migration framework (milestone 2 of `p1-data-backbone`)

## Summary

Built the forward-only, numbered SQL migration subsystem inside the `sr-search` engine — discovery (`stockroom.migrations`), a transactional runner with a runner-owned `schema_version` table (`stockroom.migrate`), and the single `warehouse.open()` chokepoint (`stockroom.warehouse`) with an `fcntl.flock` single-writer token over DuckDB's native lock plus bounded reader backoff. Succeeded: `make ci` green (90 tests, `uv.lock` untouched, REUSE 122/122).

## Requirements vs Outcome

Every milestone requirement was delivered: numbered forward-only SQL applied in ascending order, a `schema_version` record, a lazy version gate inside the open chokepoint, exclusive-lock migration, concurrency-safe reader degradation, and the harness-neutral `~/.stockroom/` warehouse home — with `0001` shipped in place (no file move). Two additions beyond the original milestone description, both deliberate and in-scope: the migrated-schema-equals-snapshot guard (added at preflight) and a `migrate=False` branch test (added at QA). Nothing was dropped or reinterpreted.

## Plan Accuracy

The plan was unusually accurate. The 10-step ordering (sweep → discovery → runner → warehouse paths → flock/backoff → open gate → concurrency → snapshot guard → green gate) held exactly as written; no step needed reordering, splitting, or adding. The file list matched. The challenges that the plan flagged (timing flakiness, atomicity, snapshot regression) were the ones that actually mattered, and each was mitigated as predicted — the concurrency suite was written outcome-based and passed stably across repeated runs.

## Creative Phase Review

The architecture decision (Option A: `fcntl.flock` writer/migrator token over DuckDB's native lock + bounded reader backoff; `schema_version` as a runner-owned bootstrap table) held up completely — the concurrency suite required **zero** production changes, which is the strongest possible signal that the design translated cleanly to code. One friction point: the creative doc specified "writers hold the flock for the connection's lifetime" but did not name a *mechanism*. At build time I found `duckdb.DuckDBPyConnection` rejects attribute assignment (C type, no `__dict__`) yet supports weakrefs, so `weakref.finalize(con, _release_flock, fd)` ties the flock release to connection finalization. This is a faithful realization of the decision, but it is worth recording that the release is GC-timing-dependent (it fires on finalization, not on `con.close()`) — an unflagged micro-unknown that resolved cleanly but could have bitten a less forgiving resource.

## Build & QA Observations

Build was smooth: strict RED→GREEN per step, one commit each, suite green throughout. The DuckDB POCs from planning meant the lock semantics behaved exactly as expected. QA found no substantive issues — only three trivial items: a module docstring still describing flock/backoff as "added in a later build step" (doc drift from incremental authoring), `_migrate_under_lock` hand-rolling the flock acquire/release that the `_flock` context manager already encapsulated (so `_flock` was, briefly, used only by tests), and the planned `migrate=False` branch being untested. All three were QA-fixable without design decisions.

## Cross-Phase Analysis

The dominant causal chain is positive: **the two planning POCs (DuckDB cross-process lock model; `fcntl.flock` auto-release on WSL-internal ext4) directly bought a first-try-green concurrency suite.** Front-loading the scary OS/DB behavior into planning meant the design was built on verified facts, not assumptions, so build and integration had nothing to discover. Conversely, the QA findings trace cleanly to the *incremental, step-numbered build style*: authoring a module across several steps invites docstrings written for the end-state (stale until the feature lands) and helpers that land a step before their production caller. These are cheap, characteristic costs of one-commit-per-step TDD — not planning gaps.

## Insights

### Technical
- **DuckDB has transactional DDL**: `CREATE TABLE` inside an explicit transaction rolls back on failure, which made `apply_pending`'s "atomic or nothing" guarantee trivial to implement and assert (the failing-migration rollback test "just works").
- **`duckdb.DuckDBPyConnection` is a C type**: it rejects attribute assignment (no `__dict__`) but supports `weakref`. `weakref.finalize` is the clean way to bind an external resource (here, the flock fd) to a connection's lifetime when you can't subclass or set attributes.
- **`flock` conflicts per open-file-description**, so lock exclusivity is unit-testable within a *single* process using two independent `os.open()` fds — no subprocess needed for the basic primitive test. The genuine cross-process lock *conflict* path, however, can only be exercised by a real subprocess (a second `duckdb.connect()` in the same process shares the instance and never conflicts) or by faking `duckdb.connect`.

### Process
- **Spike the load-bearing primitive before designing on top of it.** The two pre-plan POCs are the single clearest reason build/integration had no surprises. When a design hinges on exact OS/DB behavior, a 30-minute POC de-risks the entire downstream lifecycle.
- **When authoring a module incrementally, write each docstring for what exists *now*, not the end state.** The one piece of QA debris that recurs with step-numbered builds is forward-looking documentation that reads as false until a later step lands. Cheap to catch, cheaper to avoid.
