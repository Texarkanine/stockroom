# Project Brief

## User Story

As a macOS stockroom user, I want `stockroom dashboard` (and `--replace`) to recognize and replace a stale owned dashboard listener after a plugin-root move, so that I am not left serving a GC'd engine that 404s.

## Use-Case(s)

### Use-Case 1

Marketplace updates stockroom to a new plugin hash. Session-start runs `shim rectify` + `stockroom dashboard`. The old owned pid is SIGTERM'd and a new listener starts from the current engine.

### Use-Case 2

Operator runs `stockroom dashboard --replace` on macOS while an owned dashboard is listening. The recorded pid is replaced even when identity app_dir/version still match.

## Requirements

1. Fix [#75](https://github.com/Texarkanine/stockroom/issues/75) as specified in the issue.
2. Keep identity + “only SIGTERM the recorded pid.”
3. Make cmdline ownership check portable: `/proc` on Linux, `ps ww -p <pid> -o args=` (or equivalent) elsewhere; require `stockroom.dashboard` in the cmdline.
4. No new deps, no new protocol.
5. Add a regression so “no `/proc`” cannot silently mean “never owned.”

## Constraints

1. Minimum change confined to dashboard ownership verification / launcher path.
2. Foreign listeners remain untouched.

## Acceptance Criteria

1. When `/proc/{pid}/cmdline` is unavailable, ownership can still be verified via portable `ps` cmdline inspection.
2. Owned stale identity (and `--replace`) kill+respawn works without `/proc`.
3. Regression test covers the no-`/proc` path.
4. Existing dashboard CLI suite still passes.
