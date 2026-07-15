# Project Brief

## User Story

As a developer iterating on the stockroom dashboard, I want `make local-dashboard` to actually restart the listener (or refuse to claim a bounce) so that I load this checkout's current code instead of stale in-memory state from a long-lived process with matching `app_dir`+version.

## Use-Case(s)

### Localdev bounce after engine changes

Developer has a dashboard PID running from this checkout. They change dashboard Python/static without bumping package version, run `make local-dashboard`, and expect the new code to be served.

### Production/plugin identity no-op

Bare `stockroom dashboard` may keep the cheap “already current → no-op” path when identity matches, unless an explicit replace/force flag is passed.

## Requirements

1. Fix as described in https://github.com/Texarkanine/stockroom/issues/48
2. Prefer always-replace for `make local-dashboard` / an explicit `--replace` / `--force` flag
3. Do not print “dashboard bounced” unless a replace actually happened (or state the no-op clearly)
4. Bare `stockroom dashboard` may retain identity-aware no-op when not force-replacing

## Constraints

1. Localdev force-restart is the bug; production identity no-op is acceptable when not forced
2. Only replace owned listeners (existing ownership semantics)

## Acceptance Criteria

1. `make local-dashboard` restarts an owned listener even when `app_dir`+version match
2. Success messaging reflects actual outcome (bounce vs not restarted)
3. Bare `stockroom dashboard` without force still no-ops when identity is current
4. Tests cover force-replace vs identity no-op behavior
