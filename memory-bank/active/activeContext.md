# Active Context

## Current Task: Migration framework (milestone 2 of `p1-data-backbone`, Level 3 sub-run)

**Phase:** BUILD - COMPLETE (all steps 0–9 green; ready for QA)

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

## Next Step

- 🐱 **QA** (`/niko-qa`) runs next automatically per the L3 workflow (Build PASS → QA).
