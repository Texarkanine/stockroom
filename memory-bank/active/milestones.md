# Milestones: p2-embeddings-search

## Cross-milestone invariants & constraints

Properties every sub-run must preserve, regardless of which milestone it implements:

- **No truncation at rest.** Embeddings derive from whole stored content via bounded chunks fed to the model; the full text stays in the warehouse untouched. Truncation is a **read-time** concern only (`sr-search`). No milestone may cap, trim, or drop stored content.
- **Storage and embedding stay decoupled.** Full text lives in the store; only bounded chunks reach the model, so a 200 KB field never threatens the embedder.
- **Torch-safe contract (Phase 0).** Embedding work runs on the torch exception: torch is held out of the lock and provisioned out of band; **never run an exact sync** (`uv run --no-sync` / `--inexact`). `sentence-transformers` enters the lock via `make lock`; torch never does.
- **Locked-uv trust.** No new runtime dependency enters without a hermetic `make lock`.
- **Read surfaces open `read_only=True` through the `warehouse.open()` chokepoint** and let DuckDB reject writes — no app-level statement allow/deny-list. The embed *writer* is the one read-write consumer and also goes through the chokepoint.
- **Incremental, not from-scratch.** Re-embedding processes only new/changed content; wipe-and-rebuild of the `embeddings` table is never the normal path.
- **Schema changes only via new forward-only numbered migrations.** The VSS/HNSW index lands as the next migration (`0003`), never mutating `0001`/`0002`; the golden schema snapshot is updated as a conscious, reviewed act.
- **Harness-labeled and cross-harness by default.** Embeddings and search ride the existing `harness` column; there is no per-harness search path. A search is cross-harness by omitting the column, per-harness by filtering it.
- **Clean-room boundary.** Embedding, chunking, and VSS/search logic are reimplemented from the briefs/spike and first principles — not ported from `cursor-warehouse` (whose engine bits are the most likely upstream transliterations). Torch-specific work may be requested from the operator.
- **Test-first** (workspace TDD rule) and a **green `make ci`** gate at every milestone boundary, with `/niko-qa` passed before each reflection.

## Execution Order

Strictly sequential: each milestone builds on verified artifacts from the prior one (m2's vector search needs m1's index + embedder; m3's blend reuses m2's semantic search and m1's embedder). No parallelization, so no dependency flowchart is needed.

- [ ] **Embedding pipeline** — VSS/HNSW index migration (`0003`, cosine, experimental persistence on) plus a `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim) embedder with chunk-and-mean-pool, GPU-or-CPU device selection, `FLOAT[384]` writes through the chokepoint, and incremental re-embed of only un-embedded/changed content.
- [ ] **`sr-semantic`** — a pure vector-search read surface: embed the query, run cosine KNN over the HNSW index, join back to the owner rows, and print ranked results read-only through the chokepoint.
- [ ] **`sr-search`** — the blended keyword + semantic entrypoint: route a question to SQL / vector / blend, run keyword and semantic search, merge and rank, and apply a context-aware **read-time truncation** level so a huge field never floods the caller's context.

## Scope estimates & rationale

Advisory only — the actual classification happens at the start of each sub-run.

- **Embedding pipeline — estimated L3.** Multiple cooperating components (new `0003` migration loading the VSS extension + HNSW index, the embedder, the chunker/mean-pool, the embed writer, incremental selection) and real architectural surface (vector index persistence, the torch runtime entering the picture). New subsystem, not a contained change.
- **`sr-semantic` — estimated L2.** A self-contained new read surface that reuses m1's embedder and index — analogous to the L2 `sr-query` surface, plus query-time embedding and a vector-search query. Could tip to L3 if HNSW query ergonomics or owner-row joining prove involved.
- **`sr-search` — estimated L3.** The most logic-heavy milestone: query routing, a keyword-search mechanism (DuckDB FTS vs. `LIKE`, chosen at build time), rank fusion across two result sets, and the headline read-time-truncation feature — a genuine design decision likely warranting a creative phase.

## Open questions for preflight / sub-run creative

Not blockers — flagged so the right sub-run resolves each deliberately:

- **Chunk storage grain.** "Chunk-and-mean-pool" yields one vector per owner (`chunk_index = 0`), but the `embeddings` PK admits multiple chunks per owner. Whether to mean-pool to a single row or persist per-chunk rows is an m1 design decision; the schema accommodates both.
- **Surface packaging.** Phase 1 shipped `sr-query` as an engine module (`python -m stockroom.query`) and deferred the polished `/sr-query` skill wrapper + per-harness invocation to Phase 5. m2/m3 should follow that precedent (build `stockroom.semantic` / `stockroom.search` modules) unless a sub-run decides otherwise.
- **Keyword-search mechanism for `sr-search`** (DuckDB FTS extension vs. `LIKE`/regex) is deliberately left to the m3 build, per the roadmap's "decisions left to build time."
