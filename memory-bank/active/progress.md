# Progress

Speed up `stockroom embed` with cross-message chunk batching (no accuracy penalty) per [#54](https://github.com/Texarkanine/stockroom/issues/54), and fold in orphaned-embedding cleanup after the embed sweep per [#56](https://github.com/Texarkanine/stockroom/issues/56).

**Complexity:** Level 2

## 2026-07-15 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved: #54 primary; #56 folded in as additive hygiene on `embed_pending`
    - Classified as Level 2 (self-contained embed enhancement; research during plan)
* Decisions made
    - Fold #56 into this task unless plan discovers it pollutes the batching work
* Insights
    - Same surface as recent L2 embed work (surgical invalidation, progress logging); batching is the research-heavy half, orphan DELETE is set-oriented SQL

## 2026-07-15 - PLAN - COMPLETE

* Work completed
    - Full L2 plan in `tasks.md` (TDD behaviors, 8 implementation steps, challenges, pre-mortem)
    - CPU spike: ~16.8× for 64 short encodes batched; plateau ~batch 32; ST not bit-identical across batch vs single
* Decisions made
    - Default `EMBED_BATCH_SIZE = 32`; numeric policy = float32 near-equality; orphan cleanup = all models; fold write batching into scatter path
* Insights
    - Encode batching alone is the leverage; no CUDA on this machine — PR will document CPU timings

## 2026-07-15 - PREFLIGHT - COMPLETE

* Work completed
    - Preflight PASS WITH ADVISORY; TDD ordering amended (per-unit test-before-code); pure flatten helper as first unit
* Decisions made
    - Keep #56 in scope; do not edit untracked `.cursor/skills/stockroom-local/` mirror
* Insights
    - Original step 1 was production-first — fixed before build gate

## 2026-07-15 - BUILD - COMPLETE

* Work completed
    - Cross-message batching, set-delete, executemany, orphan cleanup, progress grain, docs, tests
    - Full suite 551 passed / 4 skipped; lint/format clean; torch-gated near-equality green
* Decisions made
    - `EMBED_BATCH_SIZE=32`; orphan DELETE all models; progress = chunk/batch lines; float32 `atol=1e-5`
* Insights
    - `make format`/`sync` drops torch — re-`make torch` before torch-gated recheck
    - DuckDB parallel `UNNEST` of two equal-length arrays works for pair deletes

## 2026-07-15 - QA - COMPLETE

* Work completed
    - Semantic review PASS; KISS: per-batch `executemany` instead of buffering all insert rows
* Decisions made
    - No substantive redesign needed
* Insights
    - Encode batching remains the leverage; write path should stay batch-aligned for memory

## 2026-07-15 - REFLECT - COMPLETE

* Work completed
    - Reflection documented; persistent memory bank left unchanged
* Decisions made
    - Million-dollar shape ≈ what shipped (select → flatten → batch encode → write → orphan DELETE)
* Insights
    - ST float32-near policy; DuckDB parallel UNNEST; preflight TDD gate earned its keep

## 2026-07-15 - PR #59 REVIEW FIXES

* Work completed
    - Opened draft PR #59; judged feedback; fixed items 4, 8, and 1 (atomic txn, quiet orphan path, batch-window test, helper split)
    - Operator measured ~2h on GTX 1070 for ~45k chunks (was ~overnight); recall unchanged
* Decisions made
    - Re-embed and orphan cleanup are separate helpers; `embed_pending` only orchestrates
* Insights
    - Set-delete + multi-batch write needs a transaction or partial owners poison incremental `NOT EXISTS`

## 2026-07-15 - ARCHIVE - IN PROGRESS

* Work completed
    - Leaving Reflect complete; entering archive for embed-batch-and-orphan-cleanup
* Decisions made
    - Archive category: enhancements/ (existing embed path improved + hygiene)
* Insights
    - None yet — archive document next
