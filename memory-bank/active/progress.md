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

## 2026-06-29 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the plan against codebase reality: TDD encoding (per-unit test-before-code), convention compliance (`render.py` location, `OUTPUT_FORMATS`/`DEFAULT_FORMAT` mirroring the `truncate` constants, `--format` mirroring `--detail`, keyword-only seams, `test_<module>.py`), dependency impact (grep-confirmed the two private renderers have no external consumers; persistent-doc references routed to REFLECT), conflict detection (public contract untouched; CLI default-shape flip is an accepted in-development change, not a published-interface break), and completeness (every PFW requirement mapped). Result: PASS.
* Decisions made
    - Folded one TDD amendment into the plan: the query CLI `--format` subprocess tests move into step 3 (written before the `query.py` wiring) so that unit is itself test-first; old step 5 merged in, renumbering to 6 steps.
    - Recorded a positive correctness finding: TSV structural safety is free because `truncate_cell` collapses all whitespace (incl. tabs/newlines) at every detail level — no extra tsv escaping needed.
* Insights
    - Advisory (not applied): a stderr row/result count for tsv, and a dict-based format dispatch registry for a future `ndjson`, were both considered and declined — the first contradicts the settled "omit for tsv" PFW decision; the second is YAGNI for three formats (`ndjson` is a named non-goal). Flagged for operator awareness only.

## 2026-06-29 - BUILD - COMPLETE

* Work completed
    - Implemented `stockroom.render` (TDD: stub → 31 failing `test_render.py` red → green) as the presentation chokepoint; relocated `query._format_table` / `semantic._format_hits` into it as the `table` branch and added `tsv`/`json`.
    - Wired both CLIs to `render` with a new `--format {tsv,json,table}` flag (default `tsv`); query CLI tests written before the wiring (preflight amendment); fixed the two semantic trailer-asserting CLI tests for the tsv default; updated `truncate.py`'s docstring reference.
    - Full `make ci` green: 266 passed, 2 skipped (torch-gated), ruff lint+format clean, lock-check clean, reuse compliant.
* Decisions made
    - Built to plan; the only deviation was cosmetic `ruff format` line-wrapping in the two new files.
* Insights
    - The relocation confirmed the standing consolidation insight: `_query_table` and `_semantic_table` now sit side-by-side in `render` and still duplicate column-alignment — the obvious next DRY (`render_table(columns, rows, *, detail)`) is now a one-module refactor, deliberately out of scope here.

## 2026-06-29 - QA - COMPLETE

* Work completed
    - Semantic review (KISS/DRY/YAGNI/completeness/regression/integrity/documentation) of the build vs. the plan. Result: PASS, no trivial fixes required.
* Decisions made
    - Confirmed the duplicated table layout + semantic row projection + score computation are the plan-sanctioned deferred consolidation (a future single `render_table`), not a defect — a piecemeal DRY now would be reworked by that consolidation; deferring whole is the better call (m3 precedent).
    - Confirmed the stale persistent-doc references (`systemPatterns.md`/`techContext.md`: `_format_table`/`_format_hits`/`(N rows)`/"column-aligned text table") are routed to REFLECT per the lifecycle, not a build deficiency.
* Insights
    - No over-engineering or YAGNI debris; `render` consolidated the print boundary rather than adding a parallel one. The defensive `raise ValueError` on an unknown `fmt` is a justified library-level guard (the CLI is already protected by argparse `choices`).
