# Algorithm/Architecture Decision: Chunk Storage Grain (per-chunk vs mean-pool)

> Supersedes the `chunk_index = 0` single-row assumption noted in
> `creative-embedding-owner-grain.md`. Owner grain (messages-only) is unchanged;
> only the *per-owner storage grain* changes here.

## Requirements & Constraints

Ranked attributes:

1. **Retrieval recall on the long tail** — a query must be able to find content buried anywhere in a long message, not just its average topic.
2. **Information preservation** — prefer the representation that loses the least; the warehouse's whole reason for existing is faithful, non-lossy capture.
3. **Storage/compute cost** — must stay trivial for a personal corpus.
4. **Forward simplicity for m2** — the chosen grain dictates how `sr-semantic` maps hits back to messages.

Corpus reality (measured 2026-06-28 against the operator's warehouse): 21,849 non-empty messages; **~75% fit in a single chunk**; ~25% are multi-chunk; 66 messages > 20 KB; max 202 KB (~hundreds of chunks); ~48 K chunks total. The `embeddings` PK `(harness, owner_table, owner_id, chunk_index)` already admits N rows per owner — **no migration needed for either grain**.

## Options Evaluated

- **Mean-pool to one row** (`chunk_index = 0`): average all chunk vectors into one per message. Original tech-brief phrasing ("one vector per source item").
- **Per-chunk rows** (`chunk_index = 0..N-1`): store one vector per chunk; at query time take the best chunk per owner (max cosine similarity / min distance) and group back to the message.

## Analysis

| Criterion | Mean-pool (1 row) | Per-chunk (N rows) |
|-----------|-------------------|---------------------|
| Long-tail recall | **dilutes** — a buried topic is 1/N of an averaged, centroid-pulled vector; can rank low | **strong** — query hits the precise chunk wherever it sits |
| Information preserved | lossy (chunks unrecoverable from a mean) | **lossless** (can always mean-pool at read time from per-chunk rows; never the reverse) |
| Storage | ~22 K vectors (~34 MB) | ~48 K vectors (~74 MB) — still trivial |
| Index cost | smaller HNSW | ~2.2× entries — negligible at this scale |
| m2 complexity | trivial (1 row = 1 message) | needs `GROUP BY owner` / `DISTINCT ON` max-sim dedup |
| Typical (75% single-chunk) message | identical to per-chunk | identical to mean-pool |

Key insights:
- For the **75%** of messages that are single-chunk, the two options are **identical** — mean-pool's only effect is on multi-chunk messages, which are exactly the long, information-dense ones where dilution hurts most.
- **Per-chunk is strictly more information**: you can reconstruct the mean from chunks at read time, but you can never recover chunks from a stored mean. Storing per-chunk defers the pooling/recall decision to m2, where it is observable, instead of baking a lossy choice into m1.
- The only cost is ~40 MB more and a group-to-owner step in m2 — both trivial. The dilution failure mode (a query matching a buried chunk that the averaged vector hides) is the precise thing semantic search must not do.

## Decision

**Selected**: **Per-chunk rows** (`chunk_index = 0..N-1`), with query-time max-sim dedup to owner (m2).

**Rationale**: Best long-tail recall and strictly lossless, at negligible extra cost, with no schema change (the PK already supports it). It moves the (reversible) pooling decision to m2 where it can be measured rather than committing m1 to a lossy mean.

**Tradeoff**: ~2.2× embedding rows and a `GROUP BY owner` max-sim step pushed into m2's `sr-semantic`. Accepted — both are cheap, and m2 owns the query surface anyway. This is a deliberate deviation from the tech-brief's "one vector per source item" phrasing, justified by the measured long-tail and the lossless-storage principle.

## Implementation Notes

- **m1 writer**: for each non-empty message, emit one `embeddings` row per chunk — `(harness, 'messages', message_id, chunk_index, embed_model, vector)` with `chunk_index` ascending from 0. No mean-pool.
- **Incremental selection**: a message needs (re-)embedding when it has **no `embeddings` row at all** for the current `embed_model` (key on owner existence, not `chunk_index = 0`). The cascade-delete (ingest writer) already operates per owner, so it correctly clears all of a message's chunks.
- **Chunking**: with the 512-token `bge-small-en-v1.5` window, target ~1200 chars / ~150 overlap as a conservative proxy (verify against the tokenizer to avoid silent within-chunk truncation; ideal is token-aware chunking to ~480 tokens).
- **m2 forward contract**: `sr-semantic` runs KNN over chunk vectors, then dedups to one hit per `(harness, owner_table, owner_id)` by min cosine distance before ranking.
