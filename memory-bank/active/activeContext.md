# Active Context

## Current Task: p3-m5-wrapper-skill-trimming
**Phase:** PLAN - COMPLETE

## What Was Done
- Full Level 2 plan written to `tasks.md`: 8 behaviors (3 engine TDD + 5 prose/artisanal), 7 implementation steps, no new technology
- Codebase survey findings folded in: the engine's missing-warehouse hint still says ``run `python -m stockroom.ingest` first`` in `query.py`/`semantic.py`/`embed.py` — quoted verbatim by the skills' error tables, so a small in-scope engine amendment swaps it to ``run `stockroom ingest` first`` (test-first; existing tests only assert `"ingest" in stderr`)
- Shared doc location decided: `skills/sr-search/references/system-model.md` (engine home; sibling-relative pointers work because committed layout = install layout; PPL-S applies automatically via the `skills/**` REUSE glob)
- `systemPatterns.md` "Cross-skill resource resolution" section identified as stale (still teaches the pre-shim `$APP_DIR` contract) — reconciliation is step 6
- m6 grep token set fixed: `APP_DIR`, `PYTHONPATH`, `uv run`, `--no-sync`, `--no-config`, `CURSOR_PLUGIN_ROOT`, `find -L`, `python -m stockroom`

## Next Step
- Preflight validation (runs automatically)
