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
