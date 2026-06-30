# Active Context

## Current Task: Output format defaults (`--format`) (p2-embeddings-search m3.5)
**Phase:** QA - COMPLETE (PASS)

## Build Outcome
- New module `skills/sr-search/src/stockroom/render.py`: `OutputFormat`/`OUTPUT_FORMATS`/`DEFAULT_FORMAT="tsv"`, public `format_query(columns, rows, *, fmt, detail)` + `format_semantic(hits, *, fmt, detail)` dispatching `tsv|json|table`, with the two relocated table renderers (`_query_table`, `_semantic_table`) as the `table` branch. `truncate_cell` applied in every format; `json.dumps(..., ensure_ascii=False)`; SQL `NULL` → JSON `null`; semantic `score` numeric; tsv/json carry no count trailer.
- `query.py`: removed `_format_table`; imports `render` + `OUTPUT_FORMATS`/`DEFAULT_FORMAT`; added `--format`; `main` prints `render.format_query(...)`; docstring updated. `semantic.py`: same shape (removed `_format_hits`, `--format`, `render.format_semantic(...)`, docstring). `truncate.py` docstring now points at `stockroom.render`.
- Tests: new `tests/test_render.py` (31); `test_query.py` (relocated 6 `_format_table` tests out); `test_query_cli.py` (+5 `--format` subprocess); `test_semantic.py` (relocated 4 `_format_hits` tests out, fixed 2 trailer-asserting CLI tests for the tsv default, +5 `--format` CLI).
- Full gate (`make ci`) green: **266 passed, 2 skipped** (torch-gated real-model), ruff lint+format clean, lock-check clean, reuse compliant.
- Deviation: only cosmetic — `ruff format` wrapped two long lines in the new `render.py` / `test_render.py`. No plan-deficiency deviations; built to plan (incl. the preflight TDD amendment ordering query CLI tests before the wiring).

## What Was Done
- Detected L4 re-entry; advanced past the completed m3 (read-time output truncation) sub-run — checked it off, cleared its ephemerals, and committed the operator's m3.5 brainstorm decision record (`planning/brainstorm/print-for-who.md`).
- Classified **Output format defaults (`--format`)** as **Level 2**: an additive, contained presentation-layer enhancement, design settled by `print-for-who.md` (so no creative phase).
- Wrote the full Level 2 plan to `tasks.md`: a new shared `stockroom.render` module (`format_query`, `format_semantic`, dispatching `tsv|json|table`, default `tsv`) that absorbs the two existing private renderers (`query._format_table`, `semantic._format_hits`) as its `table` branch and applies `truncate_cell` in every format. Both CLIs gain `--format`. Library return types unchanged. 6 ordered TDD steps; new `test_render.py` + edits to `test_query.py`/`test_semantic.py`/`test_query_cli.py`.

## Key Decisions (this session)
- **No import cycle**: `query`/`semantic` import `render` at runtime; `render` imports the dataclasses only under `TYPE_CHECKING`.
- **`render` moves, not merges**: the two table renderers relocate into `render`; DRY-ing them into one `render_table()` is an explicit non-goal (the standing m3 insight, out of scope).
- **Truncation is format-agnostic and uniform** (`truncate_cell` in every format); JSON keeps `null` for SQL NULL and a numeric semantic `score`, but otherwise stringifies cells — documented tradeoff (library is the full-fidelity surface; non-goal to change return types).
- **`(N rows)`/`(N results)` trailer is a `table`-only human affordance**; omitted from `tsv`/`json`.

## Next Step
- Reflect (`niko-reflect`) runs next per the Level 2 workflow; then STOP for the operator to run `/niko-archive`.
