# Architecture Decision: VSS Extension Provisioning & HNSW Index Location

## Requirements & Constraints

Ranked quality attributes:

1. **Offline / supply-chain safety** (highest) — a tool that reads every conversation must not pull unaudited code at runtime. No implicit network `INSTALL` on the hot path.
2. **Invariant fidelity** — "schema changes only via forward-only numbered migrations"; the HNSW index is a schema artifact and lands as `0003`. Read surfaces open through the single `warehouse.open()` chokepoint.
3. **Testability under torch-free CI** — every test that applies the migration chain (`migrated_con`, the runner's real-chain tests, `warehouse.open()` tests) must work; CI has network but no pre-cached extension.
4. **Simplicity** — the fewest moving parts that satisfy the above.

Technical constraints (spike-verified, 2026-06-28, DuckDB 1.5.4):
- `vss` installs from the network repository to `~/.duckdb/extensions/<ver>/<platform>/vss.duckdb_extension` (`install_mode = REPOSITORY`). `INSTALL` is a network op; `LOAD` is offline-safe once the file is cached.
- `hnsw_enable_experimental_persistence` is a **per-connection SET**, not persisted in the DB. It is required to create and to *modify* (insert/delete) an HNSW index on a persistent DB.
- `LOAD vss` + `SET …persistence=true` + `CREATE INDEX … USING HNSW (vector) WITH (metric='cosine')` all run cleanly **inside the runner's `BEGIN/COMMIT`** and on an `:memory:` connection.
- A persistent DB's HNSW index survives reopen; deletes/inserts against the live index work with persistence enabled.

Scope: where the index DDL lives and who installs/loads `vss`. Out of scope: the embedder, the one-time install during onboarding (Phase 4 `sr-initialize`).

## Components

- **`0003` migration SQL** — the index DDL.
- **migration runner** (`stockroom.migrate.apply_pending`) — executes migration SQL inside a transaction; stays pure forward-only mechanics, no extension knowledge.
- **chokepoint** (`stockroom.warehouse.open`) — the one place every consumer reaches the DB; already runs the lazy migration gate.
- **a new `ensure_vss(con)` helper** — `LOAD`; on failure `INSTALL` then `LOAD`; `SET hnsw_enable_experimental_persistence=true`. The single place network `INSTALL` can occur.
- **test fixtures** (`migrated_con`, and the two runner tests that apply the real packaged chain) — call `ensure_vss` before applying.

## Options Evaluated

- **Option A — fat migration**: `0003` does `INSTALL vss; LOAD vss; SET …; CREATE INDEX …`. Self-contained, but bakes a network `INSTALL` into the hot migration path executed by `open()` on every behind-the-head warehouse.
- **Option B — thin migration + chokepoint-loaded extension**: `0003` does only `SET …persistence=true; CREATE INDEX … USING HNSW`. The chokepoint calls `ensure_vss(con)` before the gate (and on every returned connection); `ensure_vss` centralizes the (rare, provisioning-time) `INSTALL`. Test fixtures call `ensure_vss` too.
- **Option C — index outside migrations**: the embed writer creates the index on demand. Violates the schema-via-migration invariant; the index would not appear in the schema golden.

## Analysis

| Criterion | A (fat migration) | B (thin migration + chokepoint) | C (writer-managed) |
|-----------|-------------------|----------------------------------|--------------------|
| Offline safety | ✗ network `INSTALL` on hot path | ✓ `INSTALL` confined to `ensure_vss`, pre-warmed by `sr-initialize` | ✓ but ad-hoc |
| Invariant fidelity | ✓ index in migration | ✓ index in migration | ✗ index not a migration |
| Testability (torch-free CI) | ✓ (network) but couples every chain-apply to a network round-trip | ✓ one `ensure_vss` seam reused by fixtures | ✓ |
| Simplicity | fewest files, worst posture | one small helper, clean seam | spreads index lifecycle into the writer |
| Risk / reversibility | hard to walk back a network call embedded in shipped SQL | low — helper is internal | medium — invariant erosion |

Key insights:
- The network `INSTALL` is the crux. The only way to keep it off the runtime hot path **and** keep the index in a migration is to separate *loading* (offline, per-connection, done by the chokepoint) from *installing* (rare, provisioning-time, centralized in one helper).
- `SET …persistence=true` being per-connection means the chokepoint must set it on **every** connection that touches the warehouse post-`0003` anyway — so the chokepoint is already the natural home for `ensure_vss`.
- The migration runner must stay extension-agnostic; the precondition "vss is loaded" is established by the caller (chokepoint or fixture), exactly as the runner already assumes "caller holds the flock".

## Decision

**Selected**: Option B — thin migration, chokepoint-loaded extension, `INSTALL` centralized in `ensure_vss`.

**Rationale**: It is the only option that satisfies the top two ranked attributes simultaneously — offline safety (no `INSTALL` in shipped migration SQL or on the runtime read path) and invariant fidelity (the HNSW index is `0003`). It adds exactly one small, reusable helper and reuses the chokepoint that already owns per-connection setup and the migration gate.

**Tradeoff**: `warehouse.open()` gains responsibility (load `vss` + set persistence on every open), and the two runner tests + `migrated_con` fixture must call `ensure_vss` before applying the real chain. Accepted: this is a thin, well-localized seam, and `ensure_vss`'s install-on-missing keeps CI/dev green (network present) while `sr-initialize` (Phase 4) pre-warms the cache so end-user runtime never needs the network.

## Implementation Notes

- **`ensure_vss(con)`** lives in `stockroom.warehouse` (next to `open`): `try: con.execute("LOAD vss") except duckdb.IOException/Error: con.execute("INSTALL vss"); con.execute("LOAD vss")`; then `con.execute("SET hnsw_enable_experimental_persistence=true")`. Idempotent.
- **`open()`** calls `ensure_vss` on the migrator RW connection (before `apply_pending`) and on every connection it returns (both read modes), so vector ops and live-index mutation are always available.
- **`0003_embeddings_hnsw_index.sql`**: `SET hnsw_enable_experimental_persistence=true;` then `CREATE INDEX embeddings_vector_hnsw ON embeddings USING HNSW (vector) WITH (metric = 'cosine');` — no `INSTALL`/`LOAD` in the file (precondition: vss loaded by caller).
- **Test fixtures**: `migrated_con` and the two `test_migrate_runner` tests that apply the *real packaged chain* (`…applies_all_packaged_on_fresh_db`, `…is_idempotent`) call `ensure_vss(con)` before `apply_pending`. Synthetic-migration tests (`tmp_migrations_dir`) are unaffected.
