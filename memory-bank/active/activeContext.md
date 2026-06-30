# Active Context

## Current Task: Output format defaults (`--format`) (p2-embeddings-search m3.5)
**Phase:** PREFLIGHT - COMPLETE (PASS)

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
- Build (`niko-build`) runs next per the Level 2 workflow. Preflight PASS; one TDD amendment folded in (query CLI tests moved ahead of `query.py` wiring); TSV structural-safety property recorded.
