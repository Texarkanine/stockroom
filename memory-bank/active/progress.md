# Progress

Sub-run m3.5 of the `p2-embeddings-search` L4 project: introduce a shared `stockroom.render` presentation chokepoint on both read surfaces (`stockroom.query`, `stockroom.semantic`) exposing `--format {tsv,json,table}` with **`tsv` as the new default** (stream-friendly for LLMs and unix pipes), `json` for structured consumers, and `table` (today's ASCII output) as an opt-in human pretty-print. The existing `--detail {compact,snippet,full}` (default `snippet`) applies in every format via the m3 `truncate_cell` policy. No schema/migration, no new runtime dependency; the only breaking change is the CLI default output shape. Decision record: `planning/brainstorm/print-for-who.md`.

**Complexity:** Level 2

## 2026-06-29 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - L4 re-entry (Step 2a): m3 (read-time output truncation) confirmed `REFLECT COMPLETE` and checked off; m3 sub-run ephemerals cleared; the operator's brainstorm decision record (`print-for-who.md`) and the newly inserted m3.5 milestone committed.
    - Classified the **Output format defaults (`--format`)** milestone as **Level 2** and wrote the determination to the memory bank.
* Decisions made
    - Level 2: an additive, contained presentation-layer enhancement — a new shared `stockroom.render` module wired into the two existing renderers with `--format`/`--detail` flags, test-first, no schema/migration, no new dependency. Design is fully settled by `print-for-who.md`, so no creative phase (which would tip it to L3). Direct precedent: the m3 truncation sub-run had the identical shape and was L2.
    - Preserved `creative/creative-search-surface-architecture.md` through the m3→m3.5 advance: it is the project-level decision record (referenced by `milestones.md` and `print-for-who.md`), not an m3 sub-run artifact.
