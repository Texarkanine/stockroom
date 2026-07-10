# Project Brief

## User Story

As a stockroom operator, I want `python -m stockroom.ingest` and `python -m stockroom.embed` to emit human-readable progress when I pass `--verbose`, so that long runs do not look hung and I can follow progress without a second terminal.

## Use-Case(s)

### Use-Case 1

Run a first full ingest over a large Cursor/Claude history tree with `--verbose`. See harness-start lines (with discovered session counts) and per-session or periodic progress until the existing end-of-run summary prints.

### Use-Case 2

Run embedding over a large pending backlog with `--verbose`. See progress while encoding proceeds, then the existing end-of-run summary.

### Use-Case 3

Run ingest/embed without `--verbose` (CI, tests, default operator use). Behavior stays quiet during the run; end-of-run summaries still print.

## Requirements

1. Add a `--verbose` flag to both `python -m stockroom.ingest` and `python -m stockroom.embed`.
2. When verbose: log when each harness (or embed phase) starts, and emit periodic or per-unit progress (e.g. `cursor: 47/200 sessions`).
3. Keep default (non-verbose) behavior quiet during the run for CI/tests.
4. Preserve existing end-of-run summaries (counts; elapsed time is optional/nice-to-have).
5. Update subprocess/CLI tests so optional verbosity is covered and the suite stays green.

## Constraints

1. Progress must not print unless `--verbose` is present.
2. Scope is progress logging only — no changes to ingest/embed correctness, watermarks, or encoding behavior.
3. Follow existing CLI/argparse and test patterns in `skills/sr-search`.

## Acceptance Criteria

1. Operator can see ingest making progress on a long run with `--verbose` without opening a second terminal.
2. Operator can see embed making progress on a long run with `--verbose` without opening a second terminal.
3. End-of-run summaries still printed (existing counts; elapsed time nice-to-have).
4. Test suite remains green; subprocess/CLI tests account for new optional verbosity.

Source: https://github.com/Texarkanine/stockroom/issues/1
