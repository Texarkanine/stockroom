# Active Context

## Current Task: Read-time output truncation (p2-embeddings-search m3)
**Phase:** PLAN - COMPLETE

## What Was Done
- L4 re-entry: m1 (embedding pipeline) and m2 (`sr-semantic` engine module) are complete and checked off; their sub-run ephemeral files were cleared on the prior advance, reflections preserved.
- Classified the **Read-time output truncation** milestone as **Level 2** (additive, contained enhancement; architecture already settled in `creative-search-surface-architecture.md`; no schema/migration).
- Produced the full Level 2 plan in `tasks.md`: a new shared `stockroom.truncate` module (`truncate_cell`, `DetailLevel`, `LEVEL_WIDTHS` `40/120/None`, `ELISION`) wired into `query._format_table` and `semantic._format_hits`, superseding `semantic._preview`/`PREVIEW_CHARS`. 7 implementation steps, TDD, new `test_truncate.py` + edits to `test_query.py`/`test_semantic.py`/`test_query_cli.py`.

## Key Decisions (this session)
- **Resolved the milestone's open question on default posture:** truncation is **on-by-default at `snippet`** for both surfaces, `--detail full` escape, `--detail compact` terser. Cap only affects over-width cells, so narrow results are visually untouched.
- **Per-cell width cap only — no global/context-aware budget** (that would be L3; explicitly out of scope).
- **Single-line collapse at every level incl. `full`** (table integrity); `full` removes only the width cap. Full fidelity lives in the data layer (`QueryResult.rows`, `SemanticHit.text`), not the rendered table.
- Data cells truncated; headers not. No new dependency (pure stdlib, `requires-python >= 3.11`).

## Next Step
- Preflight validation (`niko-preflight`) runs next per the Level 2 workflow.
