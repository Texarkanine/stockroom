# Project Brief

## User Story

As a stockroom operator, I want `stockroom embed` to finish large pending sets much faster without changing stored vectors, and I want the nightly ingest→embed path to also remove orphaned message embeddings, so GPU time is better spent and the warehouse stays consistent after interrupted rewrites.

## Use-Case(s)

### Faster nightly / manual embed

Operator runs `stockroom embed` (or the nightly job) against a warehouse with many pending messages. Encode work batches across messages so wall-clock drops on GPU (and does not regress on CPU), while vectors for a given chunk remain identical to today's pipeline.

### Orphan hygiene on embed

After a crash mid-`write_session`, embedding rows may reference message ids that no longer exist. A successful `stockroom embed` removes those orphans so the warehouse is consistent without a separate chore.

## Requirements

1. Speed up `stockroom embed` via cross-message chunk batching (and bulk writes only if measurement shows they matter), per [#54](https://github.com/Texarkanine/stockroom/issues/54).
2. No accuracy / vector-identity penalty: same model, same `chunk_text`, same stored vectors as today's pipeline (FP16 etc. not default).
3. Preserve incremental `NOT EXISTS` selection and `--full` re-embed behavior.
4. Preserve per-chunk storage grain and owner semantics (`owner_table='messages'`, `chunk_index`, replace-on-re-embed).
5. Keep the torch-free CI seam (`Encoder` injection / `FakeEncoder`).
6. `--verbose` progress may change grain but stays useful and quiet-by-default.
7. After the normal embed sweep, delete orphaned `embeddings` rows whose `(harness, owner_id)` has no matching `messages` row, per [#56](https://github.com/Texarkanine/stockroom/issues/56).
8. Document measurements (before/after, batch size, whether write batching helped) in the PR; document orphan-cleanup model scope.

## Constraints

1. Out of scope for #54: Apple Silicon/MPS device selection, model/dimension/chunk-quality changes, soft-stale search, schema migrations, exotic backends unless batching+writes prove insufficient with proven identical accuracy.
2. Out of scope for #56: wrapping all of `write_session` in an explicit transaction (separate follow-up).
3. Research and measure before coding; issue research notes are hypotheses to validate, not a mandate.
4. Prefer the smallest change that meets the goals.

## Acceptance Criteria

1. Large pending embed is materially faster wall-clock than today's per-message loop on at least one real GPU, and not slower on CPU-only.
2. Deterministic fake/contract tests stay green; chunking, incremental/`--full`, and row shape unchanged.
3. Where practical, a regression check that batched encode produces the same vectors as encoding those chunks singly (or a documented operator-accepted numeric policy).
4. PR documents what was measured.
5. Given orphan embedding rows, a successful `stockroom embed` removes them (document chosen model scope); valid embeddings for existing messages are untouched.
6. Tests lock the orphan-delete contract (including other sessions' valid vectors survive).
7. Incremental embed and `--full` still behave as today for missing/re-embed work.
