---
task_id: p2-embeddings-search (sub-run m1)
date: 2026-06-29
complexity_level: 3
---

# Reflection: Phase 2 · Milestone 1 — Embedding pipeline

## Summary

Built the m1 embedding pipeline — a torch-free-testable chunk-and-encode engine
(`stockroom.embed`) writing one `FLOAT[384]` vector per chunk through the
`warehouse.open()` chokepoint, the deferred VSS/HNSW cosine index as migration
`0003`, and session-grained embedding cascade-delete in the ingest writer. It
succeeded: all 7 plan steps landed test-first, `make ci` is green (202 passed,
1 torch-gated skip), and a real-corpus end-to-end smoke (ingest → embed → KNN →
re-ingest cascade → re-embed) passed.

## Requirements vs Outcome

Every charter requirement was delivered, and two roadmap details were
deliberately superseded by grounded creative decisions (not dropped):

- **Storage grain**: the roadmap/tech-brief said "chunk-and-mean-pool … one
  vector per source item"; we shipped **per-chunk rows** instead, justified by a
  measured long tail (max 202 KB message) and the lossless-storage principle. A
  documented, reversible improvement, not a descope.
- **Model**: the roadmap named `all-MiniLM-L6-v2`; we shipped
  `bge-small-en-v1.5` (same 384-dim, no migration) after a two-corpus empirical
  spike confirmed MiniLM was clearly weakest. Operator-resolved.
- **Incremental re-embed**: satisfied both halves of the charter (new *and*
  changed) with zero schema change via new-only selection + ingest cascade.
- One scope addition: the `--full` CLI flag (preflight radical-innovation
  advisory), mirroring `ingest --full`. Trivial surface, no complexity change.

Deferred-by-design (correctly out of m1): `tool_calls` embeddings, query-prefix,
and max-sim dedup — all forward contracts for m2.

## Plan Accuracy

The plan was accurate at the step/file/sequence level — the dependency-ordered
7-step TDD sequence executed without reordering or splitting. Two small misses,
both cheap and surfaced exactly where the process intends:

- **Ripple under-enumeration**: the plan listed `test_migrate_runner` +
  `test_warehouse_open` for the 2→3 head ripple but missed two head-coupled
  assertions in `test_warehouse_concurrency`. Caught immediately by the full
  suite; fixed in scope.
- **The one genuine surprise was a schema fact, not a design gap**: the
  `embeddings` PK `(harness, owner_table, owner_id, chunk_index)` *excludes*
  `embed_model`, so two models can't coexist at the same `chunk_index`. This
  forced "delete the owner's prior rows before insert" (replace-on-re-embed)
  rather than naive insert. The test-first pass turned what would have been a
  latent dup-key bug into a one-test correction.

Identified challenges (VSS network INSTALL, experimental-persistence durability,
torch-free testing, head ripple, writer widening) were the ones that actually
materialized — and all had been pre-de-risked by the spike + preflight, so the
build was friction-light.

## Creative Phase Review

All five creative decisions held up in code with no rework:

- **VSS provisioning (thin migration + chokepoint `ensure_vss`)**: translated
  cleanly. The one advisory left open in creative/preflight — does `LOAD vss` +
  `SET …persistence` work on a *read-only* connection? — was resolved
  affirmatively by a probe + `test_open_reader_has_vss_loaded`, so no
  writer-only scoping was needed. The design correctly predicted the chokepoint
  was the natural home (per-connection SET must run on every open anyway).
- **Per-chunk storage grain**: held; the incremental-selection note ("key on
  owner existence, not `chunk_index = 0`") was exactly right and is what the
  `NOT EXISTS` query implements.
- **Incremental re-embed (A + B)**: held, with one **inter-doc inconsistency**
  the build had to reconcile (see Cross-Phase) — the cascade doc's SQL sketch
  used `owner_table IN ('messages','tool_calls')`, but owner-grain says
  messages-only. Build correctly scoped the cascade to `'messages'`.
- **Owner grain (messages-only)** and **model selection (bge)**: held verbatim;
  the model doc's "no `uv.lock` change" prediction was confirmed by the
  lock-check gate.

Nothing was flagged as a mega-unknown that turned out trivial, and the one real
unknown (the PK behavior) was *not* flagged in any creative doc — it lived below
the design layer, in the Phase-1 schema. A schema-fact the design docs took as
given but never interrogated.

## Build & QA Observations

Build went smoothly: TDD per-unit ordering meant each step's failing tests
defined the surface before code, and the injected-`FakeEncoder` seam let the
entire pipeline (selection, per-chunk write, incremental/`--full` logic) be
tested with no torch loaded — the only torch-dependent test is `importorskip`-
gated and CI-skips. The two iteration points were both self-correcting: the PK
dup-key (corrected a test that wrongly expected model coexistence) and a KNN
test using colinear vectors (fixed to orthogonal one-hot vectors so cosine
distance actually ranks).

QA was a lint-grade pass — no substantive findings, just two trivial fixes (a
dead `@runtime_checkable` decorator with no `isinstance` use, and a one-clause
`--full` docstring drift). That QA found nothing substantive is itself a signal
that test-first + preflight front-loaded the real risk.

## Cross-Phase Analysis

- **Preflight → Build (positive chain)**: the spike that preceded preflight
  proved VSS load/persistence/HNSW-in-transaction *before* a line of pipeline
  code, so the highest-risk integration (live-index deletes, experimental
  persistence) was a known quantity at build time. This is why the build was
  friction-light — the risk was paid down a phase early.
- **Creative inconsistency → Build reconciliation**: two creative docs
  disagreed on the cascade's `owner_table` scope (incremental-doc:
  `IN ('messages','tool_calls')`; owner-grain-doc: messages-only). The build
  correctly resolved toward owner-grain (the cascade deletes only `'messages'`
  rows, since m1 only ever writes those), leaving a clean forward note: when
  tool_calls embeddings land, the cascade scope must widen with them. A
  multi-doc creative phase can carry small contradictions that only surface at
  the code that must satisfy both — the build is the reconciliation point.
- **Schema (Phase 1) → Build surprise**: the lone build surprise originated two
  phases / one milestone-set back, in the `0001` PK definition. No Phase-2
  planning artifact could have caught it without re-reading the PK columns with
  the *re-embed* use case in mind — which is the actionable lesson below.

## Process Observations

The workflow structure helped more than it cost. No phase felt like dead
overhead: the spike de-risked VSS, preflight caught the `--full` opportunity and
flagged the RO-`ensure_vss` advisory, and QA confirmed cleanliness rather than
repairing. The TDD-per-unit discipline is what converted the PK surprise from a
bug into a test correction.

## Insights

### Technical
- **Re-read the PK columns of any table you're about to write derived data
  into, against your actual write pattern.** The `embeddings` PK excludes
  `embed_model`; that single fact dictated replace-on-re-embed semantics and was
  invisible to every Phase-2 design doc because they treated the schema as a
  given. When a milestone's headline is "write rows into an existing table," the
  table's uniqueness constraints are load-bearing design input, not background.
- **`duckdb_indexes()` is lossy for HNSW**: `metric` (e.g. cosine) is *not*
  introspectable and `expressions` is a VARCHAR `'[vector]'`, not a list. A
  schema golden can lock name/table/expressions but the metric must be verified
  *functionally* (a KNN test whose ranking only holds under cosine). Worth
  remembering for any future index contract test.
- **KNN tests need orthogonal fixtures**: colinear/scaled test vectors share a
  cosine distance and make "nearest" arbitrary. One-hot/orthogonal vectors are
  the reliable way to assert a specific nearest neighbor.

### Process
- **A dependency-injection seam (here, the `Encoder` protocol + `FakeEncoder`)
  is what lets a torch-heavy feature stay under torch-free CI** — and it must be
  designed in, not retrofitted. Pre-committing to "the expensive/optional
  dependency is the only thing behind the injected boundary" kept 13 of 14 new
  tests CI-runnable. Reusable pattern for any optional-heavy-dep subsystem.
- **When a creative phase produces multiple decision docs, a quick cross-doc
  consistency pass before build would catch contradictions** (the `owner_table`
  scope mismatch) at design time rather than at the line of code that has to
  honor both. Cheap to add; would have removed a small build-time judgment call.
