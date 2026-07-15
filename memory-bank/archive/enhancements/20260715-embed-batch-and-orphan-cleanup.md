---
task_id: embed-batch-and-orphan-cleanup
complexity_level: 2
date: 2026-07-15
status: completed
---

# TASK ARCHIVE: Embed batch encode + orphan cleanup (#54 / #56)

## SUMMARY

Sped up `stockroom embed` with cross-message chunk batching (`EMBED_BATCH_SIZE = 32`) and folded orphaned message-embedding cleanup into a successful `embed_pending` sweep. CPU encode ~16.8× faster at batch 64; operator GPU confirm on GTX 1070 ~overnight → ~2h for ~45k chunks with recall unchanged. Draft PR: https://github.com/Texarkanine/stockroom/pull/59. Satisfies [#54](https://github.com/Texarkanine/stockroom/issues/54) and [#56](https://github.com/Texarkanine/stockroom/issues/56).

## REQUIREMENTS

1. Cross-message chunk batching for encode (write batching only as a cheap companion).
2. No accuracy penalty: same model/chunking; float32 near-equality policy (`atol≈1e-5`), not bit-identical ST batch vs single.
3. Preserve incremental `NOT EXISTS` selection and `--full` re-embed.
4. Preserve per-chunk storage grain and owner semantics.
5. Keep torch-free CI seam (`Encoder` / `FakeEncoder`).
6. `--verbose` progress may change grain; quiet-by-default unchanged.
7. After embed work, delete dangling `embeddings` for missing `messages` owners (all `embed_model` values).
8. Document measurements, batch size, write-batching role, orphan scope, and no-CUDA-on-build-machine note.

**Constraints:** No MPS device selection; no model/chunk-quality changes; no wrapping all of `write_session` in a transaction.

## IMPLEMENTATION

Shape: select pending → flatten via `_pending_chunk_rows` → encode windows of 32 → transactional set-delete + per-batch `executemany` insert → `_delete_orphan_message_embeddings`. PR review split re-embed vs orphan into `_embed_selected_messages` / `_delete_orphan_message_embeddings`; `embed_pending` orchestrates only. Quiet orphan path uses `count_rows=False`.

| Area | Files |
|------|--------|
| Embed | `skills/sr-search/src/stockroom/embed.py` |
| Tests | `skills/sr-search/tests/test_embed.py` |
| Docs | `docs/architecture/embeddings.md` (system-model untouched) |

## TESTING

- TDD units: flatten helper, RecordingEncoder cross-message batch, orphan cleanup (incl. empty-pending + all-models), progress grain, torch-gated BGE near-equality.
- Full suite at build: **551 passed / 4 skipped**; lint/format clean.
- `/niko-preflight` PASS WITH ADVISORY (TDD ordering amended before build).
- `/niko-qa` PASS — KISS: per-batch `executemany` instead of one giant insert buffer.
- PR #59 review fixes: atomic replace transaction, batch-window `EMBED_BATCH_SIZE+1` test, helper split.

## LESSONS LEARNED

### Technical

- `sentence-transformers` batched vs single encode is float32-near, not bit-identical — lock `atol`, do not chase exact equality.
- DuckDB: `SELECT UNNEST(a), UNNEST(b)` zips equal-length arrays for composite `(harness, owner_id)` deletes (dual-arg `UNNEST` is wrong).
- Set-delete + multi-batch write needs a transaction or partial owners poison incremental `NOT EXISTS`.

### Process

- Preflight TDD-encoding check caught a real production-first plan defect before build; worth keeping as a hard gate.
- `make format`/`sync` can drop torch mid-run — re-`make torch` before torch-gated recheck.

### Million-dollar question

If batching and orphan hygiene had been assumed from day one, `embed_pending` would still be select → flatten → encode windows → set-delete → per-batch insert → orphan DELETE — essentially what shipped. No foundational redesign beyond that shape.

## PROCESS IMPROVEMENTS

Keep the preflight “tests before production code in the plan” gate — it paid for itself on this task.

## TECHNICAL IMPROVEMENTS

None required for this contract. Soft-stale search, content-hash columns, and full `write_session` transactions remain out of scope / YAGNI here.

## NEXT STEPS

- Mark [PR #59](https://github.com/Texarkanine/stockroom/pull/59) ready / merge as desired; close or annotate [#54](https://github.com/Texarkanine/stockroom/issues/54) and [#56](https://github.com/Texarkanine/stockroom/issues/56) as delivered.
