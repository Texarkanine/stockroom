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

Each numbered unit is one TDD cycle: stub/write failing tests → stub interface if needed → implement → green. Do not implement production behavior for a unit before its tests exist and fail for the right reason.

1. **Unit: pure chunk-flatten helper (torch-free, no DuckDB)**
   - Tests first (`test_embed.py`): empty selection → `[]`; one short message → one record `(harness, owner_id, 0, text)`; one long message → N records with ascending `chunk_index` matching `chunk_text`; mixed messages preserve owner boundaries.
   - Then stub + implement in `embed.py`: e.g. `_pending_chunk_rows(selected) -> list[tuple[...]]` (name as fits codebase). Add `EMBED_BATCH_SIZE = 32` and brief numeric-policy note in module docs when introducing the batch path (unit 2), not as a freestanding behavior change.

2. **Unit: cross-message batch encode + write path**
   - Tests first (`test_embed.py`): RecordingEncoder / call-capturing wrapper — multiple single-chunk pending messages → at least one `encode` call with `len(texts) > 1` (and ≤ `EMBED_BATCH_SIZE`); written row vectors equal FakeEncoder singles for those chunks; return count = total chunks. Re-run / keep existing incremental, empty-text, multi-chunk, model-aware, and knn cases green (update only assertions that intentionally change).
   - Then implement in `embed_pending`: select → flatten via helper → encode in windows of `EMBED_BATCH_SIZE` → set-oriented delete of pending owners → `executemany` (or equivalent) inserts → return rows written. Keep `embed_chunks` for single-text use.

3. **Unit: orphan cleanup (#56)**
   - Tests first: seed dangling `embeddings` rows (no matching `messages`); seed valid rows for other owners/sessions; after `embed_pending` (including when nothing pending) → orphans gone, valid rows remain; dangling rows under a non-current `embed_model` also removed (all-models scope).
   - Then implement: after normal embed work, set-oriented `DELETE … owner_table='messages' AND NOT EXISTS (messages match)`; optional verbose delete-count line.

4. **Unit: progress grain**
   - Tests first: update/replace `test_embed_pending_on_progress_*` and CLI verbose tests for the chosen grain (start line + per-batch or equivalent); quiet default still one final count line.
   - Then implement progress emissions in `embed_pending` / confirm CLI wiring.

5. **Unit: BgeEncoder batched vs single near-equality (torch-gated)**
   - Tests first: assert `encode(batch)` ≈ per-text singles within `atol≈1e-5` (spike-backed).
   - Then no production change unless the test reveals a need (policy is documentation + test lock).

6. **Measure + document (build/PR, not a TDD unit)**
   - Before/after CPU wall-clock; confirm batch size 32; note write-batching role; numeric policy; orphan scope; no-CUDA note. Optional operator GPU confirm.

7. **Docs touch-up**
   - `docs/architecture/embeddings.md`: short notes on cross-message batch encode + orphan sweep on embed. Touch `system-model.md` only if it asserts per-message encode.

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

## Preflight Amendments

- **TDD ordering (blocking fix applied):** Restructured Implementation Plan into per-unit test-before-code cycles. Removed production-first “constants/helpers” step; pure `_pending_chunk_rows`-style helper is its own TDD unit.
- **Advisory:** Prefer the pure flatten helper (unit-tested without DuckDB) so batching/scatter logic stays thin — same pattern as surgical invalidation’s pure invalidate helper.

## Measurement notes (for PR)

- **Machine:** CPU-only (no CUDA); `BAAI/bge-small-en-v1.5` via `BgeEncoder`
- **Before/after encode:** 64 short strings: singles ~31.0s vs one batch ~1.85s (~16.8×). Batch-size sweep on 256 shorts plateaus ~32–128 (~7.2s vs ~117s at size 1)
- **Batch size chosen:** `EMBED_BATCH_SIZE = 32`
- **Write batching:** set-delete + `executemany` folded into scatter; encode was the dominant win — not measured as a separate toggle
- **Numeric policy:** ST batched vs single not bit-identical (`max_abs≈1.4e-7`); tests lock `atol=1e-5`
- **Orphan scope:** all `embed_model` values for dangling `owner_table='messages'` owners

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
