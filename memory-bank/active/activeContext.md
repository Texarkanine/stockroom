# Active Context

## Current Task: Read-time output truncation (p2-embeddings-search m3)
**Phase:** BUILD - COMPLETE

## Build Outcome
- New module `skills/sr-search/src/stockroom/truncate.py` (`DetailLevel`, `DETAIL_LEVELS`, `LEVEL_WIDTHS` `40/120/None`, `DEFAULT_DETAIL="snippet"`, `ELISION`, `truncate_cell`). Marker reports hidden count, e.g. `…(+482)`.
- Wired into `query.py` (`_format_table(..., *, detail=...)` truncates data cells; new `--detail` CLI flag; docstring updated) and `semantic.py` (`_format_hits(..., *, detail=...)` via `truncate_cell`; removed `PREVIEW_CHARS`/`_preview`; new `--detail` flag; docstring updated).
- Tests: new `tests/test_truncate.py` (11); extended `test_query.py` (+2), `test_semantic.py` (+2: full-detail render + CLI `--detail`), `test_query_cli.py` (+2: subprocess `--detail` + invalid-value exit 2).
- Full gate (`make ci`) green: **237 passed, 2 skipped** (torch-gated real-model tests), ruff lint+format clean, lock-check clean, reuse compliant.
- Deviation: only cosmetic — `ruff format` wrapped the `_format_hits` signature. The informative `…(+N)` marker was folded in during preflight (in-scope/in-level). No plan-deficiency deviations.
- Side effect: `make sync --frozen` (run by `make ci`) uninstalled out-of-lock torch from this environment (the documented torch-free CI parity). Reinstall out of band (`uv pip install torch …`) if the real-model path is needed locally.

## What Was Done (planning, retained)
- L4 re-entry: m1 (embedding pipeline) and m2 (`sr-semantic` engine module) are complete and checked off; their sub-run ephemeral files were cleared on the prior advance, reflections preserved.
- Classified the **Read-time output truncation** milestone as **Level 2** (additive, contained enhancement; architecture already settled in `creative-search-surface-architecture.md`; no schema/migration).
- Produced the full Level 2 plan in `tasks.md`: a new shared `stockroom.truncate` module (`truncate_cell`, `DetailLevel`, `LEVEL_WIDTHS` `40/120/None`, `ELISION`) wired into `query._format_table` and `semantic._format_hits`, superseding `semantic._preview`/`PREVIEW_CHARS`. 7 implementation steps, TDD, new `test_truncate.py` + edits to `test_query.py`/`test_semantic.py`/`test_query_cli.py`.

## Key Decisions (this session)
- **Resolved the milestone's open question on default posture:** truncation is **on-by-default at `snippet`** for both surfaces, `--detail full` escape, `--detail compact` terser. Cap only affects over-width cells, so narrow results are visually untouched.
- **Per-cell width cap only — no global/context-aware budget** (that would be L3; explicitly out of scope).
- **Single-line collapse at every level incl. `full`** (table integrity); `full` removes only the width cap. Full fidelity lives in the data layer (`QueryResult.rows`, `SemanticHit.text`), not the rendered table.
- Data cells truncated; headers not. No new dependency (pure stdlib, `requires-python >= 3.11`).

## Next Step
- QA review (`niko-qa`) runs next per the Level 2 workflow.
