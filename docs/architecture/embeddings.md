# Embeddings

Local vectors, the index they live in, and how search surfaces split power from judgement.

## Local vectors

The model, the index path, and why semantic recall can lag ingest.

### Model and dimensions

Embeddings use [`sentence-transformers`](https://www.sbert.net/) with [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5) at **384 dimensions**. The model is local after first fetch: once provisioned, semantic search does not need the network.

BGE-small is an *asymmetric* retrieval model: stored passages are embedded with **no** prefix; only incoming queries get the engine’s query instruction prefix. Mixing a prefixed query against wrongly-prefixed passages, or thresholding on an absolute cosine score as if it were a universal quality meter, will mislead you — scores are meaningful only **relative to each other within one query**.

Torch is required to encode; it is held out of the lock for machine-specific builds — see [Packaging](packaging.md#torch-held-out-of-the-lock).

### VSS and HNSW

Vectors live in the warehouse and are queried through DuckDB’s VSS extension over an HNSW index (migration-owned). Semantic search embeds the query with the same local model, runs cosine KNN with over-fetch, then dedups multi-chunk hits back to one row per owner message (max-sim at owner grain).

Long messages may produce several chunk vectors; that is expected. SQL `query` does not need embeddings; meaning-based recall does.

### Ingest lag and staleness

Ingest and embed are separate passes. Embed is heavier (torch + real compute) and is allowed to lag. Recent sessions may exist in SQL but be invisible to semantic search until embedded — the **silent staleness** failure mode. Weak semantic results for recent work warrant a coverage check before concluding the content is absent.

When ingest rewrite-replaces a session, it invalidates embeddings only for message ids that were removed or whose text changed. Append-only growth and unchanged history keep their vectors, so embed lag after a successful ingest leaves a small hole rather than emptying the session’s semantic coverage.

`stockroom embed` encodes pending chunks in **cross-message batches** (throughput only — same model, chunking, and float32-near vectors as single-chunk encode) and, after the normal sweep, deletes **orphaned** `owner_table='messages'` embedding rows whose `(harness, owner_id)` no longer matches a `messages` row (any `embed_model`). That heals warehouses left inconsistent by an interrupted ingest rewrite without a separate operator chore.

Nightly schedule runs both incrementally; manual catch-up is the same pair of commands — see [User Guide → Load the Warehouse](../user-guide/ingest.md).

## Search-surface split

Python modules are raw power surfaces (`query`, `semantic`, and friends). Each `sr-*` skill holds LLM-safe usage guidance. [`sr-search`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-search/SKILL.md) is a **judgement router** over `sr-query` / `sr-semantic` — there is no `stockroom.search` fusion module that pretends one ranking can replace that judgement.

The same split shows up elsewhere: `stockroom.doctor` facts vs `sr-initialize` judgement; `stockroom.schedule` mechanism vs skill consent. Engine power stays boring and composable; skills own when to call which surface.

## Read-time rendering

Both read surfaces print only through one render chokepoint. `--detail` (compact / snippet / full / raw) is orthogonal to `--format` (tsv default; json / table opt-in). Truncation markers are display bounds, not warehouse mutation — see [Warehouse](warehouse.md#no-truncation-at-rest).

## Related procedures

- Day-to-day search: [User Guide → Search](../user-guide/search.md), [Skill index](../user-guide/skills.md)
- Torch / env heal: [User Guide → Troubleshooting → Torch](../user-guide/troubleshooting/torch.md)
- CLI flags: [Advanced → CLI](../advanced/cli.md)
