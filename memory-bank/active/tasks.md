# Task: embed-batch-and-orphan-cleanup

* Task ID: embed-batch-and-orphan-cleanup
* Complexity: Level 2
* Type: simple enhancement

Speed up `stockroom embed` with cross-message chunk batching (no accuracy penalty) per [#54](https://github.com/Texarkanine/stockroom/issues/54), and delete orphaned message embeddings after the embed sweep per [#56](https://github.com/Texarkanine/stockroom/issues/56).

**Plan research (2026-07-15, this machine, CPU-only, no CUDA):** `BgeEncoder.encode` of 64 short strings is ~16.8× wall-clock faster as one batch vs 64 singles. Batch-size sweep on 256 shorts plateaus ~32–128 (~7.2s vs ~117s at size 1). Batched vs single vectors are **not bit-identical** (`max_abs≈1.4e-7`, float32 noise); treat near-equality as the numeric policy, not exact identity.

## Test Plan (TDD)

### Behaviors to Verify

- **Cross-message batch encode**: pending messages with multiple owners → `encoder.encode` is invoked with multi-chunk lists (not one call per message's tiny list only); written rows match FakeEncoder vectors for each chunk; return count = total chunks written
- **Incremental selection unchanged**: already-embedded current-model messages → second run writes 0; new message embeds only it
- **`--full` re-embed**: already-embedded content → `--full` / `full=True` replaces owners and rewrites rows
- **Replace-on-re-embed / model-aware**: owner with only `old-model` rows → selected, prior rows replaced by current model
- **Empty / whitespace messages**: skipped; no rows
- **Multi-chunk grain**: long message → N rows, `chunk_index` 0..N-1, `owner_table='messages'`
- **Batched vs single vector identity (FakeEncoder)**: same chunk set encoded via pipeline path equals encoding those chunks singly with FakeEncoder (exact)
- **Batched vs single vector identity (BgeEncoder, torch-gated)**: `encode(batch)` ≈ per-text `encode([t])` within float32 near-equality (`atol` ~1e-5); documents non-bit-identical ST behavior
- **Orphan cleanup**: embeddings whose `(harness, owner_id)` has no `messages` row → removed by successful `embed_pending`; valid owners untouched; other sessions' vectors survive
- **Orphan cleanup scope**: dangling rows for any `embed_model` under `owner_table='messages'` are removed (all models — warehouse hygiene)
- **Orphan + empty pending**: warehouse with orphans but nothing to embed → still deletes orphans; written count 0
- **Progress**: `on_progress` still useful (start + progress lines); quiet default unchanged; grain may be per-batch — update pinned progress tests accordingly
- **CLI**: missing warehouse, count line, `--full`, `--verbose` still work

### Test Infrastructure

- Framework: pytest (`skills/sr-search/pyproject.toml`)
- Test location: `skills/sr-search/tests/test_embed.py` (+ shared `FakeEncoder` in `conftest.py`)
- Conventions: torch-free FakeEncoder + `migrated_con`; torch-gated `pytest.importorskip("torch")` for real model; helpers `_insert_message` / `_seed_warehouse_message`
- New test files: none (extend `test_embed.py`)

## Implementation Plan

1. **Spike-backed constants + helpers (no behavior change yet beyond stubs if needed)**
   - Files: `skills/sr-search/src/stockroom/embed.py`
   - Changes: add `EMBED_BATCH_SIZE = 32` (from plan spike; confirm/adjust during build measurement). Optional pure helper to flatten selected messages into `(harness, owner_id, chunk_index, chunk_text)` records after `chunk_text` (keeps `embed_pending` readable). Document numeric policy in module docstring briefly.

2. **TDD: batched write path contract (FakeEncoder)**
   - Files: `skills/sr-search/tests/test_embed.py`
   - Changes: add tests that (a) a RecordingEncoder / call-capturing wrapper proves cross-message batches (encode called with >1 text when multiple single-chunk messages pending), (b) row contents equal single-encode FakeEncoder vectors, (c) existing incremental/`--full`/model-aware/empty/multi-chunk cases still express the same outcomes (update only if progress grain changes).

3. **Implement cross-message batching in `embed_pending`**
   - Files: `skills/sr-search/src/stockroom/embed.py`
   - Changes: after selecting messages, chunk all → accumulate windows of `EMBED_BATCH_SIZE` → `encoder.encode(batch)` → scatter to owners. Delete prior vectors by owner set (set-oriented `DELETE` / `UNNEST` or equivalent) before inserts for owners in the pending set. Prefer `executemany` (or multi-row insert) for chunk writes — natural with scatter; measure vs encode-only if cheap. Preserve return = rows written. Keep `embed_chunks` for single-text helpers/tests unless unused.

4. **TDD + implement orphan cleanup (#56)**
   - Files: `tests/test_embed.py`, `embed.py`
   - Changes: after normal embed work (including when written=0), run set-oriented `DELETE FROM embeddings … WHERE owner_table='messages' AND NOT EXISTS (matching messages row)` for all embed models. Optional verbose line with delete count. Tests: orphans removed; valid rows kept; other-session isolation; empty pending still cleans.

5. **Progress grain + CLI tests**
   - Files: `embed.py`, `test_embed.py`
   - Changes: emit useful progress (e.g. start message count + per-batch or chunk progress). Update `test_embed_pending_on_progress_*` and CLI verbose assertions to the new grain. Quiet default unchanged.

6. **Torch-gated near-equality regression**
   - Files: `test_embed.py`
   - Changes: extend or add beside `test_bge_encoder_encodes_to_384_on_cpu`: batched vs single within `atol=1e-5` (or measured bound from spike).

7. **Measure + document**
   - Files: PR body (and brief note in `docs/architecture/embeddings.md` only if operator-facing behavior/hygiene needs a sentence — orphan cleanup + “embed batches chunks” if docs claim per-message loop)
   - Changes: before/after wall-clock on this CPU for a representative pending set; batch size chosen (32); whether write batching mattered; numeric policy; orphan scope = all models. GPU: this env has no CUDA — document CPU results; if operator has GPU, optional confirm in PR.

8. **Docs touch-up**
   - Files: `docs/architecture/embeddings.md` (and `skills/sr-search/references/system-model.md` only if it asserts per-message encode)
   - Changes: one short note that embed encodes in cross-message batches; nightly embed also sweeps orphaned message embeddings. No schema/migration docs.

## Technology Validation

No new technology - validation not required. Plan spike already exercised existing `sentence-transformers` / torch stack on CPU.

## Dependencies

- Existing: DuckDB connection with VSS (chokepoint), injected `Encoder` / `BgeEncoder`, `chunk_text`, FakeEncoder tests
- Issues: [#54](https://github.com/Texarkanine/stockroom/issues/54), [#56](https://github.com/Texarkanine/stockroom/issues/56)
- Out of scope: MPS device selection, model/chunk quality changes, wrapping `write_session` in a transaction

## Challenges & Mitigations

- **ST batching is not bit-identical to singles**: Mitigation — document float32 near-equality policy; FakeEncoder stays exact; torch-gated `atol` test; do not enable FP16/amp.
- **No CUDA on build machine**: Mitigation — CPU non-regression + material speedup already shown (~17×); PR documents that; GPU AC satisfied by same batching mechanism / optional operator run.
- **Progress tests pin per-message lines**: Mitigation — intentionally update tests when grain changes (issue allows it).
- **Write batching vs encode batching**: Mitigation — implement set-delete + executemany as part of the batched scatter (cheap); only invest more if measurement shows writes dominate after encode batching.
- **HNSW/VSS after bulk delete/insert**: Mitigation — same APIs as today; existing suite covers KNN; orphan delete is set SQL only.
- **#56 polluting #54**: Mitigation — orphan step is additive SQL after encode path; peel out only if build stalls on it.

## Pre-Mortem

- **Plan treated issue hypotheses as design without measuring**: Already countered — plan spike ran; build step 7 re-measures after implementation.
- **Shipped bit-exact vector identity as a hard test and fought ST forever**: Plan response — numeric policy is near-equality from day one (spike proved non-identity).
- **Optimized only Python loop structure but left encode batch size = 1**: Plan response — step 3 requires multi-chunk `encode` windows; RecordingEncoder test locks it.
- **Orphan cleanup scoped to current model only, leaving stale-model orphans**: Plan response — all models for dangling message owners (documented).
- **Claimed GPU win without any timing story**: Plan response — CPU numbers in PR; explicit “no CUDA here” note rather than invented GPU figures.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
