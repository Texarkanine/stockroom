# Project Brief

## User Story

As a warehouse consumer (agent or human), I want a documented first-class CLI path to retrieve message/`tool_input` text with whitespace matching DuckDB storage so that conversation reconstruction and other fidelity-sensitive workflows do not lose newlines to `truncate_cell` collapsing.

## Use-Case(s)

### Reconstruct conversation context

An agent reconstructs a prior conversation from the warehouse. Assistant messages contain markdown tables and code blocks. The consumer needs those newlines intact without SQL `replace(chr(10), …)` workarounds.

### Exact field dump for debugging

A human runs `stockroom query` / `stockroom semantic` expecting `--detail full` (or an equivalent fidelity mode) to return whole-field text as stored, not a single flattened line.

## Requirements

1. Provide a documented, first-class way to retrieve message/`tool_input` text such that newlines (and other internal whitespace) match what is stored in DuckDB.
2. Preserve existing `tsv`/`table` column safety where single-line cells remain required (unless an explicit fidelity mode opts out).
3. Update docs/skills so consumers know which format/mode returns exact text.
4. Cover the behavior with tests (TDD).

## Constraints

1. Data at rest is already intact — this is a read-time presentation concern only (`truncate.py` / `render.py` / CLI flags).
2. Do not require SQL workarounds for the happy path.
3. Scope is the `sr-search` read surfaces (`query` / `semantic`), not the dashboard.

## Acceptance Criteria

1. There is a documented CLI path that returns message text with newlines matching DuckDB storage.
2. Existing `tsv`/`table` single-line behavior remains correct for non-fidelity modes (or is explicitly documented if changed).
3. Tests prove whitespace fidelity for the chosen path and continued collapse for table-safe paths.
4. Issue [#30](https://github.com/Texarkanine/stockroom/issues/30) acceptance sketch is satisfied.
