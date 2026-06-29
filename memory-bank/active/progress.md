# Progress

Milestone 2 of the Phase 2 (`p2-embeddings-search`) L4 project: **`sr-semantic`** —
a pure vector-search read surface. Embed the incoming query with m1's `bge-small-en-v1.5`
encoder, run cosine KNN over the `0003` HNSW index, join the nearest chunk rows back to
their owner messages, and print ranked results read-only through the `warehouse.open()`
chokepoint. Reuses m1's settled embedder + index and follows the Phase 1 `sr-query`
engine-module precedent (`python -m stockroom.semantic`); the polished skill wrapper +
per-harness invocation stay deferred to Phase 5. Cross-milestone invariants from
`milestones.md` remain binding (read-only chokepoint, harness-labeled/cross-harness by
default, torch-safe contract, clean-room boundary, test-first + green `make ci`).

**Complexity:** Level 2

## 2026-06-29 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified the second milestone (m2 — `sr-semantic`) as **Level 2 (Simple Enhancement)**.
    - Advanced the L4 milestone tracker: marked m1 (embedding pipeline) `- [x]`, deleted the m1 sub-run ephemeral files (`tasks.md`, `activeContext.md`, `progress.md`, `creative/`, `.qa-validation-status`, `.preflight-status`), preserved `milestones.md`, `projectbrief.md`, and `reflection/`.
    - Created the m2 sub-run ephemeral files (fresh `progress.md`, `activeContext.md`, `tasks.md` stub).
* Decisions made
    - L2, not L3: a self-contained new read surface that reuses m1's already-built encoder and HNSW index — directly analogous to the L2 `sr-query` surface, plus query-time embedding and a cosine-KNN query. The architecture is settled at the Phase 2 L4-plan level; the spike already proved cosine KNN works and owner-row joins are ordinary SQL, so the advisory "could tip to L3" caveat (HNSW query ergonomics / owner-row joining) does not trigger. Consistent with the milestone's advisory L2 estimate.
* Insights
    - m1 left the load-bearing primitives (the embedder, `ensure_vss` on every connection, the cosine HNSW index) already built and tested, so m2 is mostly assembling a query path over proven infrastructure — the hallmark of an L2 contained change.

## 2026-06-29 - PLAN - COMPLETE

* Work completed
    - Wrote the full L2 plan to `tasks.md`: a new `stockroom.semantic` read surface mirroring the `sr-query` engine-module shape (library `run_semantic_search` + `con`/encoder injection, a runnable `main`), reusing `stockroom.embed`'s `Encoder`/`BgeEncoder`/`EMBED_*`. TDD plan = ~13 torch-free behaviors + 1 torch-gated end-to-end; 6 dependency-ordered, test-first steps; technology validation (no new deps, no `uv.lock` change).
* Decisions made
    - **Apply bge's asymmetric query prefix by default** (`QUERY_PREFIX`), threadable to `""` for the deterministic `FakeEncoder` — captures the spike's measured +0.037 MRR query-side win with no passage-side change.
    - **Index-accelerated KNN + over-fetch (`limit*OVERFETCH`) + Python max-sim dedup** to one-row-per-owner — keeps the HNSW top-k acceleration *and* discharges the dedup obligation m1 deferred, vs. a `GROUP BY MIN` that would defeat the index.
    - **Display-preview-only output**; context-aware read-time truncation stays m3's headline feature (no-truncation-at-rest invariant untouched). Promote `FakeEncoder` to `conftest.py` (DRY); in-process CLI tests per the `embed` precedent (no subprocess file).
* Insights
    - The two flagged unknowns (owner-row join, HNSW query ergonomics) both resolved without new architecture: the join is ordinary SQL on `owner_id == message_id`, and the index is preserved by over-fetching before the dedup. The only genuine design lever — the query prefix — was already settled by the m1 cross-corpus spike, so m2 stays a contained L2.
