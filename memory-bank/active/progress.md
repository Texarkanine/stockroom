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

## 2026-06-29 - PLAN - COMPLETE

* Work completed
    - Surveyed the two target renderers (`query._format_table`, `semantic._format_hits`), their tests, `conftest.py` fixtures, `truncate.py`, and the Python floor; grep-confirmed the two private renderers are referenced only within their own modules, their tests, and one `truncate.py` docstring (no external consumers).
    - Wrote the full Level 2 plan to `tasks.md`: a new shared `stockroom.render` chokepoint (`format_query`/`format_semantic`, `tsv|json|table` dispatch, default `tsv`) absorbing the two relocated table renderers, applying `truncate_cell` in every format, with `--format` added to both CLIs and library return types untouched. 7 ordered TDD steps; new `test_render.py` + edits to `test_query.py`/`test_semantic.py`/`test_query_cli.py`.
* Decisions made
    - No import cycle: runtime edge is one-way `query`/`semantic` → `render`; `render` imports the dataclasses only under `TYPE_CHECKING`.
    - `render` *moves* the two table renderers, it does not merge them into a shared `render_table()` (explicit non-goal; the standing m3 consolidation insight stays out of scope).
    - Truncation is uniform/format-agnostic; JSON keeps SQL `NULL` → `null` and a numeric semantic `score`, otherwise stringifies cells via `truncate_cell` (documented tradeoff — library is the full-fidelity surface).
    - The `(N rows)`/`(N results)` trailer is a `table`-only human affordance, omitted from `tsv`/`json`; the `tsv` default flip is itself tested and the two semantic trailer-asserting CLI tests are updated.
