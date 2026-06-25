# Active Context

## Current Task: Migration framework (milestone 2 of `p1-data-backbone`, Level 3 sub-run)

**Phase:** REFLECT - COMPLETE (ready for operator-gated Archive)

## What Was Done

- Built the forward-only migration subsystem test-first through all 10 ordered plan steps, one commit per step:
  - **Step 0** convention sweep: dropped `from __future__ import annotations` from the existing 8 engine/test files (pure refactor).
  - **`stockroom.migrations`** — `Migration` NamedTuple + `migrations_dir()` + `discover()` (ascending `NNNN_*.sql`, numeric order, non-conforming names ignored).
  - **`stockroom.migrate`** — runner-owned `schema_version` bootstrap table, `current_version()` (0 before bootstrap), forward-only `apply_pending()` (per-migration transaction, atomic rollback, idempotent, no-op when ahead).
  - **`stockroom.warehouse`** — the single `open()` chokepoint: harness-neutral home (`STOCKROOM_HOME`-overridable, auto-created), `_flock` single-writer token, `_open_with_backoff` (exp backoff + jitter → typed `WarehouseBusyError`), double-checked lazy gate.
  - **Concurrency suite** — real subprocesses: reader degradation, writer drain, racing-migrator serialization (no double-apply), typed terminal error.
  - **Snapshot guard** — a freshly opened warehouse's product schema byte-matches m1's `0001_snapshot.json` (excluding `schema_version`).
- Updated `memory-bank/techContext.md` Warehouse Schema note to point at the now-real `warehouse`/`migrate`/`migrations` modules and the two-layer lock.

## Key Implementation Decision (build-time)

- **Writer flock lifetime via `weakref.finalize`.** `duckdb` connections reject `setattr` (C type, no `__dict__`) but support weakrefs, so the writer's flock releases when the returned connection is finalized — honoring the creative doc's "flock held for the connection's lifetime" without a wrapper type. No deviation from the architecture; readers stay lock-free at the coordination layer.

## Verification

- `make ci` green: sync, `lock --locked` (uv.lock **untouched** — stdlib-only, no new dependency), ruff lint + format-check clean, **89 tests passed** (26 new for m2), REUSE compliant (122/122). Concurrency suite stable across repeated runs.

## QA Outcome

- **PASS** with three trivial fixes (stale docstring removed; `_migrate_under_lock` refactored onto the `_flock` ctx manager for DRY; `migrate=False` branch test added). No substantive/blocking findings. `make ci` green — 90 tests, `uv.lock` untouched, REUSE 122/122.

## Reflection Outcome

- Wrote `reflection/reflection-p1-data-backbone-m2-migration-framework.md`. Plan was highly accurate (10-step order held exactly); creative Option A held with zero production changes in the concurrency suite. Key insights: the two planning POCs bought a first-try-green concurrency suite; DuckDB has transactional DDL (atomic `apply_pending` for free); `weakref.finalize` ties the flock to a `duckdb` connection's lifetime (no `setattr` on the C type).
- Reconciled persistent files: added the deferred **"Two-layer warehouse lock behind a single open() chokepoint"** pattern to `systemPatterns.md`. `techContext.md` was already repointed during build; `productContext.md` unaffected.

## Next Step

- 🧑‍💻 **Archive is operator-gated.** This is an L4 sub-run (milestone 2 of `p1-data-backbone`); milestone 1 was archived inline by the L4 capstone flow. Next: run `/niko` to continue to the next milestone (the capstone archive handles ephemeral cleanup). Reflect is a terminal node — stopping here for operator input.
