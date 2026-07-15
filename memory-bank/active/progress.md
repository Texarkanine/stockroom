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
