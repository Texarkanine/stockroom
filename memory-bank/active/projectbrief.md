# Project Brief

## User Story

As a maintainer, I want Codecov coverage badges in the stockroom README (and the CI/collection plumbing to back them) so that coverage is visible at a glance and tracked over time.

## Use-Case(s)

### Use-Case 1

A visitor to the GitHub README sees Codecov badge(s) reflecting current coverage for the project's test-run root(s).

### Use-Case 2

CI collects coverage from the project's test runners and uploads it to Codecov so badges and PR coverage feedback stay current.

### Use-Case 3

Maintainers decide whether the public surface is one aggregated badge, separate engine/dashboard badges, or both — informed by how Codecov treats multi-root uploads and by the a16n multi-flag reference.

## Requirements

1. Collect coverage from stockroom's test-run roots (today: engine pytest under `skills/sr-search/`, dashboard JS via `make test-dashboard-js` / Node 22).
2. Upload coverage to Codecov from CI.
3. Decide aggregate vs per-root presentation (a16n's flag-based multi-root setup is the reference: `../a16n`, especially `codecov.yml` + per-package upload/badge pattern).
4. Add the chosen Codecov badge(s) to the root README (alongside the existing REUSE badge).
5. Wire any local Make/docs hooks needed so contributors can generate coverage the same way CI does, if that falls out of the design.

## Constraints

1. Do not invent a third test infrastructure — extend the existing pytest and Node test roots.
2. Prefer patterns already proven in a16n (Codecov Flags, carryforward, `codecov/codecov-action`) unless stockroom's two-root shape clearly wants something simpler.
3. Coverage collection must not break the existing `make test` / CI green path.
4. Product runtime behavior is out of scope; this is CI/tooling/docs only.

## Acceptance Criteria

1. CI produces and uploads coverage artifacts Codecov accepts.
2. README shows working Codecov badge(s) matching the chosen aggregation policy (badges may 404 until first successful upload + token — that is expected and documented if needed).
3. The aggregate-vs-separate decision is recorded and reflected in `codecov.yml` / badge URLs.
4. Existing tests continue to pass with coverage collection enabled.
