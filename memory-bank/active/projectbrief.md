# Project Brief

## User Story

As a stockroom operator, I want all warehouse timestamps stored as UTC and clients to render them into my local timezone so that Claude and Cursor session activity times line up with real wall-clock experience.

## Use-Case(s)

### Use-Case 1

Operator on America/Chicago opens the dashboard Recent Sessions list. A Claude session that ran at ~10:22 PM CDT displays as ~10:22 PM (not 3:22 AM). Cursor sessions continue to display correctly.

### Use-Case 2

Metrics that filter or bucket by activity time (`ACTIVITY_TIME_SQL` consumers: trends windows, wrapped peak hours, etc.) treat Claude and Cursor timestamps on the same UTC clock so window edges and hour-of-day buckets are not skewed by local offset.

## Requirements

1. All timestamps persisted in the warehouse MUST be UTC (naive UTC wall clock is acceptable if the contract is documented and consistent; prefer an unambiguous UTC representation end-to-end).
2. Clients (dashboard JS and any other display surfaces) are responsible for interpreting stored UTC and rendering into a timezone when desired.
3. Fix the Claude skew described in [issue #32](https://github.com/Texarkanine/stockroom/issues/32): `started_at` (UTC-as-naive) must not be mixed with local `source_mtime` under `COALESCE`, and the UI must not treat UTC hours as local.
4. Audit and align other consumers of `started_at` / `source_mtime` / `ACTIVITY_TIME_SQL` so they inherit the same UTC contract.
5. Existing rows may need a migration or re-ingest path if local `source_mtime` values would remain wrong under the new contract — choose the minimal correct approach.

## Constraints

1. Scope is the timezone contract for warehouse timestamps and their display/metric consumers — not a redesign of ingest or dashboard features.
2. Follow TDD for all code changes.
3. Prefer clean-break consistency over preserving incorrect local-naive `source_mtime` semantics.

## Acceptance Criteria

1. On a non-UTC machine (e.g. America/Chicago), Claude Recent Sessions "started" times match real session wall clock (within normal formatting), not UTC hours shown as local.
2. Cursor Recent Sessions times remain correct under the same UTC-in-DB / client-renders-zone contract.
3. `source_mtime` and authored timestamps (`started_at` / `ended_at` / related) are stored as UTC consistently across harnesses.
4. Tests cover the UTC storage contract and client/display interpretation sufficiently to prevent regression of the offset skew.
5. Other `ACTIVITY_TIME_SQL` consumers do not reintroduce mixed local/UTC clocks.
