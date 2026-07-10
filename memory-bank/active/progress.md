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
