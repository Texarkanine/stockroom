# Architecture Decision: Dashboard Non-Migrating Open Path

## Requirements & Constraints

L4 preflight finding 1, deferred to this sub-run: `warehouse.open(read_only=True)` runs the lazy migration gate, so a reader behind the schema head *transparently becomes the migrator*. The session-start hook launches the dashboard, so a plain read-only open would transitively violate the hook-discipline invariant ("never migrates"). The dashboard needs an open that never migrates and refuses cleanly when it can't serve current-schema data.

Ranked quality attributes:

1. **Invariant safety** — no dashboard code path may migrate or write, structurally (not by convention).
2. **Chokepoint discipline** — every consumer reaches the DB through `stockroom.warehouse`; version-comparison policy must not leak into consumers (no consumer touches `_latest_version` or reimplements the gate).
3. **Errmsg ratchet** — refusals name the next action with exact commands.
4. **Simplicity** — mechanism pieces already exist (`open(migrate=False)`, `current_version`, `discover`); this is composition, not new machinery.

Scope boundary: this decision covers the *engine-side* open contract and the *HTTP-side* refusal shape. The m2 front-end's rendering of the refusal is out of scope (it just needs a stable JSON shape).

## Components

`warehouse.open()` already has the non-migrating half (`migrate=False`) and the version primitives (`current_version`, private `_latest_version`). Missing: a composed "open read-only, refuse if behind" entry and a typed staleness error.

## Options Evaluated

- **A — Chokepoint variant: `warehouse.open_current(read_only=True)`** — a small public function beside `open()`: opens with `migrate=False`, compares `current_version(con)` to the discovered head, closes and raises a typed `WarehouseStaleError` (naming `stockroom migrate`) when behind, else returns the connection.
- **B — Dashboard-local check** — the dashboard calls `open(read_only=True, migrate=False)` and compares versions itself via `stockroom.migrate.current_version` + `stockroom.migrations.discover`.
- **C — Mode flag on `open()`** — e.g. `open(read_only=True, migrate="require-current")`, folding refusal into the existing gate.

## Analysis

| Criterion | A: `open_current()` | B: dashboard-local | C: mode flag |
|-----------|--------------------|--------------------|--------------|
| Invariant safety | Structural (never calls the gate) | Structural but re-implemented per consumer | Structural |
| Chokepoint discipline | Policy stays in `warehouse` | **Leaks gate policy into a consumer**; invites drift when a second non-migrating reader appears | Policy stays in `warehouse` |
| Simplicity | ~15 lines + one exception class | Similar lines, wrong home | Overloads `migrate`'s type (bool → bool\|str), muddies the common path |
| Reusability | Any future hook-launched reader uses it as-is | None | Same as A but worse API |

Key insights:

- The existing `migrate=False` escape already proves the gate is optional; what's missing is only the *refusal*. That is version-comparison policy, which per the chokepoint pattern belongs in `warehouse`, not in each reader.
- A missing warehouse file is the same product situation as a behind-head warehouse ("not servable at current schema") but a different next action (`stockroom ingest` vs `stockroom migrate`). DuckDB read-only open on a missing file raises `IOException` — checking `warehouse_path().is_file()` first (the `query.py` precedent) gives the honest message.

## Decision

**Selected**: Option A — `warehouse.open_current(read_only=True)` plus a typed `WarehouseStaleError(RuntimeError)`.

**Rationale**: keeps schema-staleness policy at the chokepoint (quality attribute 2), is structurally migration-free (attribute 1), and is the smallest composition of existing pieces (attribute 4). Reusable by any future never-migrate reader.

**Tradeoff**: one more public name on the warehouse module. Accepted — it is the honest counterpart of `open()` for gate-forbidden consumers.

## Implementation Notes

- `WarehouseStaleError` carries the versions (`current`, `latest`) and a message naming `stockroom migrate` (errmsg ratchet).
- `open_current(read_only=True)`: resolve path → `_open_with_backoff` read-only → `ensure_vss` → if `current_version(con) < _latest_version()`: close, raise `WarehouseStaleError`. Read-only only for now (the dashboard is its only consumer); no write-mode variant until someone needs it.
- Dashboard HTTP mapping (all `/api/*` endpoints):
  - Missing warehouse file → HTTP 503, JSON `{"error": "no warehouse yet", "action": "run `stockroom ingest`"}`.
  - `WarehouseStaleError` → HTTP 503, JSON `{"error": "warehouse schema is behind", "action": "run `stockroom migrate`"}`.
  - `WarehouseBusyError` → HTTP 503, JSON naming retry. One stable refusal shape: `{"error": str, "action": str}`.
- The dashboard opens per request (DuckDB open on an existing file is cheap; fresh-on-every-refresh is a product requirement and per-request opens avoid holding a read lock that would starve the nightly writer).
