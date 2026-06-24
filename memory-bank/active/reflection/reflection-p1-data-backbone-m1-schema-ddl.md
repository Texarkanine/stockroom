---
task_id: p1-data-backbone-m1-schema-ddl
date: 2026-06-24
complexity_level: 3
---

# Reflection: Schema field enumeration + locked DDL

## Summary

Locked the five-table, harness-labeled DuckDB warehouse schema as `migrations/0001_initial_schema.sql`, authored test-first with a 46-test contract suite (including a golden locked-schema snapshot) and durable native-format transcript fixtures for milestone 3. Succeeded cleanly: `make ci` green, QA PASS with a single trivial in-phase fix.

## Requirements vs Outcome

Delivered exactly the milestone-1 scope: the DDL at its final packaged path (no later move), the `schema_con` fixture (read+execute, no migration runner), the contract test suite, the enumeration record (carried from creative), and the shared real/pathological transcript fixtures. No requirements dropped. One in-scope *addition* originated in preflight, not build: the golden-snapshot test (`0001_snapshot.json`) — it over-delivers on "locked DDL" and hands milestone 2 a regression guard. The Project Brief's sixth table (`plan_documents`) was dropped, but that decision was made and operator-approved back in creative; build simply honored it.

## Plan Accuracy

The plan was accurate and well-sequenced. The 11 ordered steps executed in order with no reordering or splitting. The file list was exact (the only product artifact really was one `.sql` file; everything else was tests + fixtures + a docs pointer). The Technology-Validation POC done during planning meant zero DuckDB surprises at build time — `VARCHAR[]`, `JSON`, `FLOAT[384]`, composite PKs, `list_contains`, `json_array_length`, token `SUM`, and the subagent self-link all behaved as the POC predicted. The challenges register predicted the real friction (FK enforcement avoided, VSS deferred, fixture-secrets risk handled by scrubbing).

## Creative Phase Review

Every binding creative decision held up under code with no friction:
- **Uniform `message_id = {session_id}#{ordinal}`** — expressed cleanly as composite PKs + an `ordinal` column; the identical-content-distinct-ids test confirms the anti-collision property.
- **Model split by grain** (`messages.model` vs `sessions.models VARCHAR[]`) — translated directly; the no-faking test asserts both NULL-sides.
- **Typed BIGINT tokens, native LIST, JSON only for `tool_input`** — all three storage-policy calls implemented verbatim and each is now guarded by a behavioral test.
- **No FKs / no harness CHECK / no HNSW index** — encoded as deliberate omissions, each with a test proving the consequence (harness-neutrality; fixed-size vector).

No creative decision needed re-exploration. The empirical enumeration was thorough enough that the schema shape never wobbled during build.

## Build & QA Observations

Build was smooth and genuinely test-first: each constraint/behavior went RED before the DDL or test query made it GREEN. Two self-inflicted, immediately-caught issues: (1) a JSON array-length test used `len()` on a JSON value (string length) instead of `json_array_length` — a query bug, fixed on the spot; (2) the first snapshot introspection swept in DuckDB's internal catalog tables because they live in `main`, fixed by filtering `internal = false`. QA found one real piece of semantic debris: a parametrized PK test carried an unused `pk_cols` argument plus a comment describing a variation the code didn't perform — fixed by varying a non-PK column so the test now proves PK-only collision.

## Cross-Phase Analysis

- **Planning POC → frictionless build.** Validating the exact DDL feature-set on the real DuckDB version during planning is why build hit no engine surprises. The cost of the POC was repaid many times over.
- **Preflight → durable artifact.** The snapshot test was a preflight "radical-innovation" finding; catching it pre-build meant it was designed in cleanly (one introspection helper, reused for both the test and snapshot generation) rather than bolted on.
- **Creative rigor → clean QA.** Because the schema decisions were fully resolved with data before build, QA had no design-level findings — only a stylistic test-debris item. The causal chain "thorough enumeration → stable schema → behavioral tests that just pass" held.
- **Snapshot generation coupling.** Generating `0001_snapshot.json` by importing the test's own `_introspect_schema` (rather than a parallel script) guarantees the golden file and the test can never diverge — a small decision that removes a whole class of future drift.

## Process Observations

The L3 workflow fit this task well. Preflight earned its keep (it produced the snapshot-test idea and corrected the licensing step). No phase felt like overhead. The "accrete a pointer per landed artifact" cut-gate strategy worked: techContext gained one precise pointer rather than absorbing schema prose.

## Insights

### Technical
- **DuckDB introspection (`duckdb_columns()`) returns system catalog tables in the `main` schema.** Any schema-snapshot/introspection logic must filter `internal = false` (or to an explicit table allow-list) or it captures `sqlite_master`, `duckdb_*`, etc. This will recur in milestone 2's migration framework if it does any catalog reflection.
- **A golden schema snapshot generated *via the test's own introspection function* is a high-leverage, low-cost lock.** It makes "locked DDL" literal and self-consistent. Worth reusing for every future migration (`000N_snapshot.json`).
- **JSON in DuckDB: use the right function for the shape.** `->`/`->>` extract values; array length needs `json_array_length`, not `len()` (which measures the JSON text). Easy to get wrong, cheap to test.

### Process
- **A planning-time POC against the real engine version is the single highest-ROI step for a DDL/data-contract task** — it converts "will this type/feature parse?" unknowns into build-time certainties. Make it standard for schema work.
- **Parametrized tests are a quiet home for debris.** An argument can fall out of use while the case list stays plausible-looking. When reviewing parametrized tests, check that every parameter is actually consumed by the body.
