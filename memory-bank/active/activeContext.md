# Active Context

## Current Task: embed-batch-and-orphan-cleanup
**Phase:** BUILD - COMPLETE

## What Was Done
- Implemented cross-message chunk batching (`EMBED_BATCH_SIZE=32`), set-oriented owner delete, `executemany` inserts, orphan cleanup (all models), per-batch `--verbose` progress
- Pure `_pending_chunk_rows` helper; FakeEncoder + torch-gated near-equality tests
- Docs: `docs/architecture/embeddings.md` batching + orphan sweep note
- Verification: format/lint clean; **551 passed, 4 skipped** (torch-gated reconfirmed after `make torch`); CPU encode spike ~16.8× at batch 64

## Files modified
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/embed.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_embed.py`
- `/home/mobaxterm/git/stockroom/docs/architecture/embeddings.md`

## Deviations
- Progress grain changed to chunk/batch lines (issue-allowed); message `i/N` lines retired
- Numeric policy: float32 near-equality (`atol=1e-5`), not bit-identical

## Next Step
- QA review (autonomous for L2)
