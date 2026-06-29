# Active Context

## Current Task: Phase 2 · Milestone 2 — `sr-semantic` (`p2-embeddings-search`, sub-run m2)

**Phase:** `PLAN - COMPLETE` — full L2 plan written to `tasks.md`; preflight runs next (autonomous).

## What Was Done

- Classified m2 (`sr-semantic`) as **Level 2** and advanced the L4 tracker (m1 checked off, ephemerals cleared).
- Wrote the L2 plan: a new `stockroom.semantic` read surface (`python -m stockroom.semantic "<q>"`) mirroring the `sr-query` engine-module shape, reusing `stockroom.embed`'s encoder. Covers query-embedding (with bge's asymmetric query prefix), index-accelerated cosine KNN over the `0003` HNSW index, **max-sim owner dedup** (the obligation m1 deferred), owner-row join, a ranked display table, and a torch-free test seam (`FakeEncoder` promoted to `conftest.py`).
- 6 implementation steps, ~13 torch-free behaviors + 1 torch-gated edge; no new dependencies (no `uv.lock` change expected).

## Key Plan Decisions

- **Apply bge's query prefix by default** (`QUERY_PREFIX`), threadable to `""` for the deterministic fake — captures the spike's measured +0.037 MRR query-side win without a passage-side change.
- **Over-fetch (`limit*OVERFETCH`) + Python dedup** to one-row-per-owner: keeps the HNSW top-k acceleration *and* satisfies max-sim dedup, vs. a `GROUP BY MIN` that would defeat the index.
- **Display preview only** for output; context-aware read-time truncation stays m3's headline feature (no-truncation-at-rest invariant untouched).
- In-process CLI tests (`main(..., encoder_factory=FakeEncoder)`) per the `embed` precedent — no subprocess CLI file.

## Next Step

- Preflight validation (invoke `niko-preflight`) runs automatically.
