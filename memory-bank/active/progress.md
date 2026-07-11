# Progress

Add a documented first-class CLI path so `stockroom query` / `stockroom semantic` can return message/`tool_input` text with whitespace matching DuckDB storage, instead of always collapsing newlines via `truncate_cell` ([issue #30](https://github.com/Texarkanine/stockroom/issues/30)).

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent against issue #30
    - Classified as Level 2 Simple Enhancement
    - Initialized ephemeral memory-bank files
* Decisions made
    - Level 2: self-contained change in truncate/render/CLI presentation; pick among issue's proposed directions during plan
* Insights
    - Current collapse-at-every-detail-level is intentional for table/TSV safety; the gap is missing an exact-text escape hatch, not a broken store

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Wrote Level 2 implementation + TDD plan in `tasks.md`
    - Mapped touchpoints: `truncate.py`, `render.py`, query/semantic CLIs, `sr-query`/`sr-semantic` skills
* Decisions made
    - Add `--detail raw` (opt-in fidelity) rather than changing `full` or format-coupling collapse
    - Canonical recipe `--format json --detail raw`; tsv/table+raw allowed but documented as unsafe
* Insights
    - `DETAIL_LEVELS` already drives argparse choices — extending the constant is the main wiring

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated TDD encoding, conventions, dependency impact, completeness
    - Amended plan: json.loads fidelity assertions; required systemPatterns update
* Decisions made
    - PASS — proceed to build
* Insights
    - Dashboard `truncate_cell(..., "snippet")` is unaffected; no parallel truncation path to conflict with
