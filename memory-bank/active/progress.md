# Progress

Milestone 1 of the Phase 2 (`p2-embeddings-search`) L4 project: the **embedding
pipeline**. Land the deferred VSS/HNSW cosine index as a new forward-only
migration (`0003`, experimental persistence on so deletes work against a live
index), build a local `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim)
embedder with chunk-and-mean-pool and GPU-or-CPU device selection, and write
`FLOAT[384]` vectors through the `warehouse.open()` chokepoint — re-embedding
only un-embedded/changed content. Built on the Phase 0 torch contract and the
Phase 1 warehouse. Binding sub-run findings live in `milestones.md` (torch-free
embedder testability, offline VSS provisioning, `owner_id` grain, the `0003`
migration-head ripple, and a mandatory load-bearing-primitive spike).

**Complexity:** Level 3

## 2026-06-28 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified the first unchecked milestone (m1 — embedding pipeline) as **Level 3 (Intermediate Feature)**.
    - Created the m1 sub-run ephemeral memory-bank files (fresh `progress.md`, `activeContext.md`, `tasks.md` stub); preserved the L4 `projectbrief.md` and `milestones.md`.
* Decisions made
    - L3, not L4: the decision tree's "architectural implications" question is satisfied at the *Phase 2 L4 plan* level; within this sub-run the architecture is settled and the remaining unknowns (VSS provisioning, index persistence, `owner_id` grain) are resolved in a creative/spike phase — the L3 hallmark. Consistent with the preflight bound (each milestone ≤ L3) and the advisory L3 estimate.
* Insights
    - The preflight directive to open with a load-bearing-primitive spike (offline `vss`, HNSW cosine + live-delete persistence, CPU `all-MiniLM-L6-v2` encode) maps cleanly onto the L3 creative/exploration phase.

## 2026-06-28 - CREATIVE - COMPLETE

* Work completed
    - Ran the mandated load-bearing-primitive spike against DuckDB 1.5.4 on this machine: `vss` INSTALL/LOAD OK; HNSW cosine KNN correct; DELETE/INSERT against a live index + survive-reopen OK with experimental persistence; `LOAD/SET/CREATE INDEX USING HNSW` run inside the runner's `BEGIN/COMMIT` and on `:memory:`. Confirmed `INSTALL` is the network op (`REPOSITORY` mode), `LOAD` is offline-safe. The CPU encode leg was already proven in `planning/spikes/o9-torch/` (torch absent here by design — not re-run).
    - Resolved all 3 open questions (high confidence), each documented under `memory-bank/active/creative/`.
* Decisions made
    - **VSS provisioning/index**: thin `0003` (index only); chokepoint `ensure_vss(con)` LOADs + sets persistence on every open and centralizes the rare network `INSTALL`; fixtures call `ensure_vss` before the real chain. Keeps `INSTALL` off the runtime hot path while keeping the index a migration.
    - **Owner grain**: messages only for m1 (`owner_id=message_id`, `chunk_index=0`); `tool_calls` deferred (additive later via the existing `owner_table`).
    - **Incremental**: select owners lacking a current-`embed_model` vector (new + model change) + session-grained embedding cascade-delete in `ingest.writer` (edits), no schema column.
* Insights
    - The schema's `owner_table` and the per-connection persistence SET both pointed at the same architecture: defer breadth (messages-only), and make the chokepoint own `vss` loading since it already owns the migration gate and per-connection setup.

## 2026-06-28 - PLAN - COMPLETE

* Work completed
    - Wrote the full L3 plan to `tasks.md`: component analysis (4 engine modules + a bounded test-infra ripple), two pinned diagrams (data flow, torch-free test seam), TDD test plan (~14 behaviors + 2 integration), a 7-step ordered implementation plan, technology validation, and challenges/mitigations.
* Decisions made
    - Implementation order is dependency-led: pure chunker → injected-encoder pipeline (torch-free) → `ensure_vss`+`0003`+golden → head-version ripple → writer cascade → real-model encoder+CLI (torch-gated) → docs.
    - No `uv.lock` change (vss is a DuckDB extension, not a Python dep); torch stays out of the lock; CI stays torch-free.
* Insights
    - The migration-head bump is the one test-suite-wide event; the coupled assertions are a small, enumerated set (`test_migrate_runner`, `test_warehouse_open`) plus a new `0003_snapshot.json` — exactly as the Phase-1 reflection predicted.

## 2026-06-28 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the implementation plan against codebase reality: **PASS (with advisory)**; wrote `.preflight-status`.
    - Caught and fixed a blocking **TDD-plan-encoding** gap: the test-first cycle was stated only in the plan preamble. Restructured all 7 steps with explicit (a) test-first / (b) implement substeps so the plan cannot be followed code-first.
    - Verified convention compliance (module/migration/snapshot precedents), the enumerated migration-head ripple, no conflicts, and requirement completeness.
* Decisions made
    - Folded the radical-innovation finding (an `--full` re-embed flag mirroring `ingest --full`) into step 6 — small, in-scope, precedent-aligned.
    - Recorded two build-time advisories: verify `ensure_vss`'s `SET`/`LOAD` succeed on read-only connections (m2 readers need vss); make the `0003` golden capture an index section since columns are unchanged from `0002`.
* Insights
    - The lone blocking risk was plan *encoding*, not design — the spike + creative had already de-risked the substance, so preflight's value here was forcing per-unit test-first rigor before the build gate.
