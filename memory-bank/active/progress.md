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

## 2026-06-29 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - Validated the L2 plan against codebase reality: **PASS** (no blocking findings); wrote `.preflight-status`. TDD encoding (per-unit test-first), convention compliance (mirrors `query.py`/`embed.py`), dependency impact (imports-not-mutates `embed.py`; **no migration/schema ripple** unlike m1), conflict detection, and completeness all clear.
* Decisions made
    - **Folded in** a relevance-**score** display column (cosine similarity `1 - distance`) — friendlier than raw distance, display-only, no query cost (Step 4 amended + a test added).
    - **Advisory, not changed**: deferred an optional `--harness` per-harness filter to m3 (avoid scope creep on a pure vector-search engine module — the invariant's "per-harness by filtering" fits m3's user surface); deferred extracting a shared table renderer (`_format_hits` vs `query._format_table`) until a third need exists (YAGNI).
* Insights
    - The single biggest contrast with m1 is the **absence of a migration**: no `000N` snapshot, no head-version assertions, no test-suite-wide ripple — m2 is purely additive engine + test code, which is exactly why it classified and validated cleanly as L2.

## 2026-06-29 - BUILD - COMPLETE

* Work completed
    - Built `stockroom.semantic` strictly test-first across all 6 plan steps: shared `FakeEncoder` → `conftest.py`; `embed_query`/`QUERY_PREFIX`; `SemanticHit` + `run_semantic_search` (index KNN → `limit*OVERFETCH` over-fetch → Python max-sim owner dedup → owner-row join, read-only owns-connection path); `_format_hits` (similarity score + single-line preview + `(N results)` trailer) and `main` (`-k/--limit`, empty/limit/missing-warehouse guards before the encoder is built); a torch-gated real-model end-to-end; and docs (`techContext`, `systemPatterns`, `SKILL.md`).
    - Full gate green: lock-check clean (**no `uv.lock` change**), `ruff check` + `ruff format --check` clean, REUSE compliant (168/168), **222 passed / 0 skipped** (torch present locally, so the two `importorskip`-gated tests ran instead of skipping — the real-model paraphrase search ranked its message first).
* Decisions made
    - **Torch-safe gate**: ran the `make ci` steps with `--no-sync` rather than `make ci`, because `make ci` → `make sync` (`uv sync --frozen`) would strip the operator's out-of-band torch. Identical checks, preserves torch, and exercises the gated tests.
    - **`EMBED_DIM` in the distance cast** (DRY with the schema width; removes an unused import). `_format_hits` kept as a small dedicated renderer (not merged with `query._format_table` — the preflight YAGNI advisory).
* Insights
    - Every preflight prediction held: no migration ripple, the row-value `(harness, message_id) IN (…)` owner join worked first try, and the over-fetch-then-dedup design used the index while discharging m1's deferred max-sim obligation. The one genuinely *validating* moment was the torch-gated end-to-end actually running locally — confirming m1's prefix-free passages and m2's prefixed query land in the same space, which the deterministic fake can't prove.
