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

- [x] **Embedding pipeline** — VSS/HNSW index migration (`0003`, cosine, experimental persistence on) plus a `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim) embedder with chunk-and-mean-pool, GPU-or-CPU device selection, `FLOAT[384]` writes through the chokepoint, and incremental re-embed of only un-embedded/changed content.
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

## Preflight findings (binding on sub-runs)

Validated against codebase reality on 2026-06-28. The milestone decomposition **passed** (complete, non-overlapping, dependency-ordered, each ≤ L3). These findings are not plan defects — they are concerns the named sub-run must resolve in its own plan/creative phase:

- **[m1 · high] Embedder must be unit-testable without torch.** CI (`.github/workflows/ci.yml`) syncs the torch-free locked env and runs `pytest` with `--no-sync`; torch is never present. So the bulk of m1's tests must run with **no torch** — favor the Phase 1 con-injection precedent (`run_query(sql, *, con=None)`): a pure chunker + an *injected* encoder, with a thin real-model integration test gated/skipped when torch is unavailable. A design that hard-requires torch to run any embedder test will not pass `make ci`.
- **[m1 · high] VSS extension provisioning vs. the offline/supply-chain posture.** DuckDB's VSS extension is normally `INSTALL`ed from the network extension repository, which tensions with the "local-only, no CDN, supply-chain-safe" posture. m1 must consciously decide how `vss` is provisioned (bundle / vendor / one-time install at `sr-initialize`) rather than letting an implicit network `INSTALL` slip in.
- **[m1 · medium] `embeddings.owner_id` grain for `tool_calls`.** `0001` says `owner_table ∈ {messages, tool_calls}` with `owner_id` "references the owner row's `message_id`" — but `tool_calls` is keyed by `(…, message_id, ordinal)`, so `message_id` alone is ambiguous. m1 must decide the keying (e.g., a composite `owner_id`, or embed messages only in v1) before writing vectors.
- **[m1 · medium] A new migration `0003` is a test-suite-wide event.** Adding the VSS/HNSW index advances the migration head and will ripple into every test coupled to "latest version" / "which migrations exist" / the schema golden snapshot (`test_schema_0002.py`, `test_warehouse_open.py`, `test_migrate_runner.py`, `test_migrations_discovery.py`). Budget head-version-assertion updates + a new `0003_snapshot.json` as part of m1, per the Phase 1 reflection's process note.
- **[m1 · preflight-added directive] Spike the load-bearing primitives first.** Phase 1's single strongest lesson: every milestone that opened with a real-engine/data probe built frictionlessly. m1 **must** open with a throwaway probe validating the three dominant unknowns together before committing design: (1) `vss` install/load under the offline posture, (2) an HNSW **cosine** index with experimental persistence that supports **deletes against a live index**, and (3) a CPU `sentence-transformers` (`all-MiniLM-L6-v2`) encode yielding a 384-vector. This is guidance to the m1 sub-run, not a separate milestone (a spike is not independently deliverable).
- **[TDD] Per-unit test-first ordering is enforced inside each sub-run**, not here — consistent with the L4 model (no dedicated L4 build/QA/reflect phases). The cross-milestone invariants make test-first + green `make ci` binding at every boundary.
