# Task: exact-message-text-retrieval

* Task ID: exact-message-text-retrieval
* Complexity: Level 2
* Type: simple enhancement

Add a documented first-class CLI fidelity path so `stockroom query` / `stockroom semantic` can return message/`tool_input` text with whitespace matching DuckDB storage ([issue #30](https://github.com/Texarkanine/stockroom/issues/30)). Today `truncate_cell` collapses all internal whitespace at every `--detail` level (including `full`), which is intentional for `tsv`/`table` column safety but leaves no exact-text escape hatch.

**Design choice:** add `--detail raw` — unbounded width, **no** whitespace collapse — as an explicit opt-in fidelity level. Keep `compact`/`snippet`/`full` behavior unchanged (`full` remains unbounded + single-line). Canonical recipe: `--format json --detail raw` (JSON carries real `\n`). `tsv`/`table` + `raw` remain allowed but are documented as structurally unsafe when cells contain newlines/tabs.

## Test Plan (TDD)

### Behaviors to Verify

- [B1 raw preserves whitespace]: `truncate_cell("a\n\nb  c", "raw")` → `"a\n\nb  c"` (newlines and multi-space intact)
- [B2 raw is unbounded]: `truncate_cell("x" * 5000, "raw")` → full string, no elision marker
- [B3 existing levels still collapse]: `truncate_cell("a\n\nb  c", level)` → `"a b c"` for `compact`/`snippet`/`full`
- [B4 DETAIL_LEVELS includes raw]: `DETAIL_LEVELS` / `LEVEL_WIDTHS` / `DetailLevel` advertise `raw` with width `None`
- [B5 query json+raw fidelity]: `format_query(..., fmt="json", detail="raw")` with a cell containing newlines → after `json.loads`, the cell string equals the original (stdout may show JSON-escaped `\n`; assert on the decoded value)
- [B6 semantic json+raw fidelity]: `format_semantic(..., fmt="json", detail="raw")` → after `json.loads`, `text` equals the original including newlines
- [B7 tsv/table non-raw unchanged]: `format_query` / `format_semantic` at `full`/`snippet` still collapse whitespace (regression)
- [B8 CLI accepts raw]: `stockroom query --detail raw …` and `stockroom semantic --detail raw …` exit 0 (argparse accepts the choice)
- [B9 empty/null edge]: empty string → `""`; SQL `NULL` still renders as JSON `null` / TSV `"NULL"` under `raw`
- [B10 skills document the path]: `sr-query` / `sr-semantic` skill docs name `--detail raw` (with `--format json`) as the exact-text handoff

### Test Infrastructure

- Framework: pytest (configured in `skills/sr-search/pyproject.toml`)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_<module>.py`; pure unit tests for truncate/render; CLI helpers in `test_query_cli.py` / `test_semantic.py`
- New test files: none — extend `test_truncate.py`, `test_render.py`, `test_query_cli.py`, and semantic CLI coverage in `test_semantic.py`

## Implementation Plan

1. [x] **Extend truncate contract (failing tests first)**
   - Files: `skills/sr-search/tests/test_truncate.py`, `skills/sr-search/src/stockroom/truncate.py`
   - Changes: add tests for B1–B4; then add `"raw"` to `DetailLevel`, `DETAIL_LEVELS`, `LEVEL_WIDTHS` (`None`); change `truncate_cell` so collapse runs for all levels **except** `raw`; update module docstring to distinguish `full` (unbounded, single-line) vs `raw` (unbounded, exact whitespace)

2. [x] **Render fidelity for json+raw (and regression for other combos)**
   - Files: `skills/sr-search/tests/test_render.py`, `skills/sr-search/src/stockroom/render.py`
   - Changes: add tests B5–B7, B9; update render module docstring so `--detail` axis documents `raw`; no structural change expected beyond whatever flows from `truncate_cell` (render already calls it uniformly)

3. [x] **CLI argparse + help text**
   - Files: `skills/sr-search/tests/test_query_cli.py`, `skills/sr-search/tests/test_semantic.py`, `skills/sr-search/src/stockroom/query.py`, `skills/sr-search/src/stockroom/semantic.py`
   - Changes: B8 — assert `--detail raw` is accepted; update `--detail` help strings to mention `raw` as the exact-whitespace escape hatch (CLIs already use `choices=DETAIL_LEVELS`, so acceptance is mostly automatic once the constant expands)

4. [x] **Document the first-class path in skills + system model**
   - Files: `skills/sr-query/SKILL.md`, `skills/sr-semantic/SKILL.md`, `skills/sr-search/references/system-model.md` (brief truncation note), `memory-bank/systemPatterns.md` (required: the “`--detail compact|snippet|full`” line becomes factually wrong once `raw` ships)
   - Changes: B10 — document `--format json --detail raw` as the exact-text recipe; clarify that `full` is unbounded length but still single-line; update worked-example handoffs that currently say `--detail full` for whole-field retrieval when fidelity matters; surgically update `systemPatterns.md` detail-level enumeration

5. [x] **Verify**
   - Run targeted pytest for truncate/render/query/semantic, then full `make ci` (or project-equivalent) before declaring build done

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing `stockroom.truncate` / `stockroom.render` chokepoint (no parallel truncation path)
- CLI surfaces already bind `--detail` to `DETAIL_LEVELS` — extending the constant is the primary wiring
- Skill docs are the user-facing contract for agents reconstructing conversations

## Challenges & Mitigations

- **Challenge: `tsv`/`table` + `raw` can embed raw newlines/tabs and break column structure.** Mitigation: do not refuse (keeps detail orthogonal to format); document `--format json --detail raw` as the canonical path; leave `full` as the table-safe unbounded level.
- **Challenge: existing tests assert collapse at every level (`test_collapses_whitespace_and_newlines_at_every_level`).** Mitigation: narrow that test to non-`raw` levels; add explicit `raw` preservation cases (TDD step 1).
- **Challenge: skill/docs currently teach `--detail full` as “whole field”.** Mitigation: update handoff recipes so agents that need exact whitespace use `raw`; keep `full` documented as unbounded single-line for scan/refetch when structure does not matter.
- **Challenge: dashboard also imports `truncate_cell` at `snippet` only.** Mitigation: out of scope; confirm no dashboard call site passes a new level; no dashboard changes planned.

## Pre-Mortem

- **Plan failed because we changed `full` instead of adding `raw`, silently breaking consumers that relied on single-line `full` output:** Plan already chooses opt-in `raw` and leaves `full` unchanged — hold that line in build/QA.
- **Plan failed because agents still refetch with `--detail full` and think newlines are missing from the DB:** Covered by Challenge on skill/docs — treat skill handoff updates as load-bearing acceptance work, not optional polish.
- **Plan failed because we over-scoped into TSV escaping / a separate `--exact` flag / format-coupled collapse:** Cut scope: one new detail level through the existing chokepoint; no new CLI flag axis; no TSV escape scheme.

## Preflight Amendments

- B5/B6 assert fidelity on `json.loads` decoded values (not raw stdout bytes).
- `memory-bank/systemPatterns.md` detail-level line update is required, not optional.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA
