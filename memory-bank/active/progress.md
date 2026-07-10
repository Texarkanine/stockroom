# Progress

Move Cursor auto-heal/dashboard hook from `workspaceOpen` to `sessionStart`, and fix hook bootstrap so rectify runs under a uv-selected `>=3.11` interpreter instead of bare system `python3` (Xcode 3.9 on Mac).

**Complexity:** Level 2

## 2026-07-10 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified and approved
    - Classified as Level 2
    - Ephemeral memory bank initialized
* Decisions made
    - Level 2: bug fix spanning Cursor hook event + dual-harness bootstrap + packaging tests/docs
    - Use uv to **select** interpreter for bootstrap; do not restore `uv run --no-sync` for rectify
* Insights
    - Shim already uses uv for the engine; the failure is only the PYTHONPATH bootstrap `python3`
    - Empty-`.venv` footgun from heal-after-move remains the reason rectify must not use `uv run --no-sync`

## 2026-07-10 - PLAN - COMPLETE

* Work completed
    - Linear TDD plan in `tasks.md` (packaging tests → both hook JSONs → docs)
    - Technology validation: `uv python find --project` selects `>=3.11` without creating empty `.venv`
* Decisions made
    - Bootstrap: `PY="$(uv python find --project \"$APP\" --no-config)"` then `"$PY" -m stockroom` — not bare `python3`, not `uv run --no-sync`
    - Cursor event: `sessionStart` only (no dual-event fallback)
    - Claude gets the same bootstrap; nested schema unchanged
* Insights
    - Cursor docs: `sessionStart` is agent/composer lifecycle; `workspaceOpen` is IDE workspace lifecycle — Mac 3.10.x not firing the latter matches operator evidence

## 2026-07-10 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against hooks, packaging tests, Cursor docs (`sessionStart` schema)
    - Confirmed TDD ordering (tests before hook JSON edits)
    - Wrote `.preflight-status` = PASS
* Decisions made
    - No plan amendments; keep inline hook commands (no new script artifact)
* Insights
    - `sr-initialize` still uses bare `python3` in an interactive shell — out of scope; advisory only

## 2026-07-10 - BUILD - COMPLETE

* Work completed
    - Packaging tests updated for `sessionStart` + `uv python find` bootstrap
    - Cursor + Claude hook JSON updated; docs/systemPatterns/shim docstring
    - 467 passed, 3 skipped; ruff clean
* Decisions made
    - `PY=$(uv python find --project "$APP" --no-config)` without quoting the substitution (paths are space-free plugin hashes)
* Insights
    - None beyond plan
