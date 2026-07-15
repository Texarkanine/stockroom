---
task_id: embed-batch-and-orphan-cleanup
date: 2026-07-15
complexity_level: 2
---

# Reflection: embed-batch-and-orphan-cleanup

## Summary

Delivered cross-message chunk batching for `stockroom embed` (#54) plus orphan embedding cleanup (#56). CPU encode ~16.8× faster at batch 64; FakeEncoder and float32-near BGE contracts green.

## Requirements vs Outcome

All brief requirements met: batch encode, no accuracy penalty (near-equality policy), incremental/`--full` preserved, torch-free CI seam kept, orphan sweep (all models), docs + measurement notes for the PR. GPU AC documented as no-CUDA-here with CPU material speedup.

## Plan Accuracy

Plan spike held: encode batching was the leverage; write batching was a cheap companion. DuckDB pair-delete needed parallel `UNNEST` (not dual-arg `UNNEST`). Progress grain change was intentional and test updates were straightforward.

## Build & QA Observations

TDD units landed cleanly after preflight fixed production-first ordering. QA only nudged per-batch `executemany` for memory alignment. `make format`/`sync` dropped torch mid-run — re-`make torch` before torch-gated recheck.

## Insights

### Technical
- `sentence-transformers` batched vs single encode is float32-near, not bit-identical — lock `atol`, do not chase exact equality.
- DuckDB: `SELECT UNNEST(a), UNNEST(b)` zips equal-length arrays for composite `(harness, owner_id)` deletes.

### Process
- Preflight TDD-encoding check caught a real plan defect before build; worth keeping as a hard gate.

### Million-Dollar Question

If batching and orphan hygiene had been assumed from day one, `embed_pending` would still be select → flatten → encode windows → set-delete → per-batch insert → orphan DELETE — essentially what shipped. No foundational redesign beyond that shape.
