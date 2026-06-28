# Project Brief: Phase 2 — Embeddings and Search

**Task ID:** `p2-embeddings-search`
**Source:** [`planning/roadmap.md`](../../planning/roadmap.md) → "Phase 2 — Embeddings and Search"

## User Story

With the faithful data backbone landed in Phase 1 (a populated, queryable single-file DuckDB warehouse under `~/.stockroom/`), make that content **findable by meaning**. Build the embedding pipeline and the two search surfaces that turn the warehouse from "queryable by SQL" into "searchable by intent."

## Scope (from the roadmap)

Three test-first milestones, built on the Phase 0 torch contract:

1. **Embedding pipeline** — local `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), chunk-and-mean-pool of long text, `FLOAT[384]` storage, DuckDB VSS/HNSW cosine index (experimental persistence enabled so deletes work against a live index), GPU-or-CPU, and incremental re-embed of new content only.
2. **`sr-semantic`** — pure vector search over the HNSW index, named so a keyword-search-seeker won't grab it by mistake.
3. **`sr-search`** — the blended keyword + semantic entrypoint: picks SQL, vector, or a blend per the question, merges and ranks, and applies a context-aware read-time truncation level.

## Done When (phase success criteria)

- Semantic and blended search return relevant results over the real ingested history.
- New content re-embeds **incrementally** rather than from scratch.
- Read-time truncation is **demonstrably a feature** — full content preserved in the store, sensibly trimmed on output.

## Grounding

- **Authoritative detail:** `planning/roadmap.md` (Phase 2) and `planning/tech-brief.md` remain the grounding truth during the build.
- **The `embeddings` table already exists**, forward-declared in `0001_initial_schema.sql` (`harness`, `owner_table`, `owner_id`, `chunk_index`, `embed_model`, `vector FLOAT[384]`); the HNSW/VSS index is explicitly deferred to Phase 2.
- **Engine home:** `skills/sr-search/src/stockroom/`; read surfaces open `read_only=True` through the single `warehouse.open()` chokepoint (Phase 1 pattern).
- **Torch contract:** embedding work runs on the Phase 0 torch exception — torch held out of the lock, provisioned out of band, never an exact sync.
