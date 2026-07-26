# Progress

Add an opt-in, one-shot backfill of legacy Cursor `state.vscdb` composers into the warehouse ([#84](https://github.com/Texarkanine/stockroom/issues/84)), selecting every composer missing from the warehouse rather than only nonzero-token ones, while leaving core nightly ingest and Cursor watermarks untouched.

**Complexity:** Level 3

## 2026-07-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Loaded persistent memory bank; confirmed no in-flight task
    - Probed live `state.vscdb` to size the corpus: 934 backfill candidates (418 nonzero-token, 516 tokenless), 2025-03 → 2026-07, out of 2,065 composers total
    - Clarified and got operator approval on intent; wrote `projectbrief.md`
    - Classified the work as Level 3
* Decisions made
    - Nonzero bubble `tokenCount` is not a selection gate (deviation from #84 as written)
    - Ponytail intensity tempered: minimal but production-quality; no code golf
* Insights
    - The aborted `enhance-cursor-tokens` work (`memory-bank/archive/enhancements/20260722-cursor-token-counts-vscdb.md`) already established the harness facts this build depends on: `cursorDiskKV` over `ItemTable`, hybrid prefix/scan reads on slow mounts, and that contemporary bubbles carry `{0,0}` tokens
    - The operator's `~/.config/stockroom/config.toml` still contains a `[cursor].state_vscdb` key that current `stockroom.config` does not read — a leftover from the aborted branch, and a natural configuration hook to reconsider during planning
