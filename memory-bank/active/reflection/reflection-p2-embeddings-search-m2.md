---
task_id: p2-embeddings-search-m2
date: 2026-06-29
complexity_level: 2
---

# Reflection: Phase 2 · Milestone 2 — `sr-semantic` (pure vector search)

## Summary

Built `stockroom.semantic` (`python -m stockroom.semantic "<q>" [-k N]`): a read-only pure-vector-search surface that embeds the query with the bge query prefix, runs cosine KNN over the m1 `0003` HNSW index, max-sim-dedups to one row per owner message, joins back to `messages`, and prints a similarity-scored ranked table. Succeeded — clean L2 lifecycle, 222 passed (0 skips), no schema change.

## Requirements vs Outcome

Every milestone requirement delivered: query embedding, cosine KNN over the HNSW index, owner-row join, ranked read-only output, **and** the max-sim owner dedup m1 explicitly deferred. One in-scope addition beyond the bare milestone, introduced at preflight and built: a relevance **score** (cosine similarity = `1 - distance`) display column. Two advisories were consciously *not* built (deferred to m3): an optional `--harness` per-harness filter, and extracting a shared table renderer. Nothing was dropped or descoped.

## Plan Accuracy

The plan was accurate end-to-end; the 6-step sequence ran without reordering or backtracking. Both flagged unknowns dissolved exactly as predicted: the owner-row join was ordinary SQL (the row-value `(harness, message_id) IN (…)` form worked first try), and the HNSW ergonomics were handled by over-fetch-then-dedup. The only "surprises" were trivial and mechanical: `ruff format` rewrapped two new files, and `make ci` had to be sidestepped (it depends on `uv sync --frozen`, which would strip the operator's out-of-band torch) by running the identical gate with `--no-sync`.

## Build & QA Observations

Friction-light. Test-first surfaced no design gaps; every test moved red→green on the first implementation pass. The single genuinely *validating* event was the `importorskip("torch")`-gated end-to-end actually running locally (torch present) — it confirmed the asymmetric contract (m1's prefix-free passages + m2's prefixed query land in the same space), which the deterministic `FakeEncoder` structurally cannot prove. QA was lint-grade: one stray docstring double-space, no substantive findings.

## Insights

### Technical
- **Per-chunk storage forces a read-time dedup, and the index shapes how.** A `GROUP BY owner MIN(distance)` is the "obvious" max-sim dedup but defeats the VSS top-k acceleration; over-fetching `limit * OVERFETCH` chunk hits in the index-friendly `ORDER BY distance LIMIT n` form and deduping in Python keeps the index *and* the one-row-per-owner grain. The storage-grain decision (m1) and the search-dedup decision (m2) are two halves of one design — worth deciding together next time derived data is stored at a finer grain than it is read.
- **A deterministic fake can prove mechanics but not geometry.** `FakeEncoder` (hash→vector) verifies chunking/selection/dedup/ranking exactly, but an *asymmetric* model's query-prefix/passage-no-prefix proximity is a real-embedding-space property. The torch-gated end-to-end is not optional polish — it's the only test that can validate the prefix decision.

### Process
- **The `make ci` ⟂ torch-contract tension is now concrete, not theoretical.** `make ci` → `make sync` (`uv sync --frozen`) strips out-of-band torch. m1 never hit it (torch absent then); m2 did (torch present). Running the gate steps with `--no-sync` is the torch-safe equivalent and is *strictly better* coverage (gated tests run instead of skipping). This should probably become the documented local-gate recipe, or `make ci` should gain a torch-preserving variant — a candidate finding for a later phase.

### Million-Dollar Question
- If "one vector per chunk + max-sim read-time dedup" had been a foundational assumption from the start, the cleanest shape is roughly what we built — a shared retrieval helper (`embed_query` → index KNN → dedup-to-owner) that both `sr-semantic` and the m3 `sr-search` blend call, rather than m3 re-deriving the KNN+dedup. m2 deliberately stopped short of that abstraction (only one caller exists today — YAGNI), but the `run_semantic_search` seam is shaped so m3 can lift the dedup core into a shared helper when it becomes the second caller. That's the elegant end-state; building it now would have been speculative.
