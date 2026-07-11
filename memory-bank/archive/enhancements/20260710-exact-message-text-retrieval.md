---
task_id: exact-message-text-retrieval
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: exact-message-text-retrieval

## SUMMARY

Added `--detail raw` as an opt-in exact-whitespace escape hatch through the existing `truncate_cell` / render chokepoint, documented `--format json --detail raw` as the canonical fidelity path for message/`tool_input` text, and left `full` as unbounded single-line. Satisfies [issue #30](https://github.com/Texarkanine/stockroom/issues/30). Delivered with clean TDD build and QA pass (`make ci`: 510 passed, 3 skipped).

## REQUIREMENTS

1. Documented first-class CLI path returning message/`tool_input` text with whitespace matching DuckDB storage.
2. Preserve existing `tsv`/`table` column safety for non-fidelity modes (`compact`/`snippet`/`full` still collapse whitespace).
3. Update skills/docs so consumers know which mode returns exact text.
4. Cover fidelity and regression with tests (TDD).

**Constraints:** Read-time presentation only; no SQL workarounds for the happy path; scope is `query` / `semantic`, not the dashboard.

## IMPLEMENTATION

Chose additive `--detail raw` over changing `full` or format-coupling collapse. `raw` is unbounded width with no whitespace collapse; `full` stays unbounded + single-line. Extending `DETAIL_LEVELS` / `LEVEL_WIDTHS` alone wired both CLIs via existing `choices=DETAIL_LEVELS`. Canonical recipe: `--format json --detail raw` (JSON carries real `\n`); `tsv`/`table` + `raw` allowed but documented as structurally unsafe.

**Key files**

| Area | Files |
|------|--------|
| Truncate | `skills/sr-search/src/stockroom/truncate.py`, `tests/test_truncate.py` |
| Render | `skills/sr-search/src/stockroom/render.py`, `tests/test_render.py` |
| CLIs | `skills/sr-search/src/stockroom/query.py`, `semantic.py`; `tests/test_query_cli.py`, `test_semantic.py` |
| Docs | `skills/sr-query/SKILL.md`, `skills/sr-semantic/SKILL.md`, `skills/sr-search/references/system-model.md`, `memory-bank/systemPatterns.md` |

## TESTING

- TDD: B1–B4 truncate → B5–B7/B9 render → B8 CLI argparse → B10 skill docs.
- Fidelity assertions use `json.loads` decoded values (not raw stdout bytes).
- `make ci` green: **510 passed, 3 skipped**.
- `/niko-preflight` PASS (amendments: json.loads assertions; required systemPatterns update).
- `/niko-qa` PASS — no substantive findings; one-branch change in `truncate_cell` plus docs honesty.

## LESSONS LEARNED

### Technical

When a detail level is advertised as “whole field” but still mutates content (whitespace collapse), agents distrust the warehouse. Separating *length* (`full`) from *fidelity* (`raw`) keeps table safety without lying about exact text.

### Process

Nothing notable — plan sequence and file list were accurate; extending `DETAIL_LEVELS` alone wired both CLIs. Skill handoff updates were the load-bearing acceptance work, not optional polish.

### Million-dollar question

If exact-text retrieval had been a foundational assumption, `--detail` would have been two axes from day one (budget × fidelity), or `full` would have meant exact-and-unbounded with format-specific escaping for TSV. An additive `raw` level is the least-disruptive version of that insight for an already-shipped orthogonal `--detail`/`--format` design.

## PROCESS IMPROVEMENTS

None — Level 2 flow (plan → preflight → build → QA → reflect → archive) fit this enhancement cleanly.

## TECHNICAL IMPROVEMENTS

None required. A separate `--exact` flag or TSV escape scheme remains YAGNI; keep detail orthogonal to format.

## NEXT STEPS

- Close or annotate [issue #30](https://github.com/Texarkanine/stockroom/issues/30) as delivered.
- None otherwise — standalone L2 complete.
