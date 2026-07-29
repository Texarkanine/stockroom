# Active Context

## Current Task: fix-cli-version-release-please-sync
**Phase:** BUILD - COMPLETE

## What Was Done
- TDD: packaging lockstep + marker tests failed on stale `0.1.2`, then passed after fix
- Bumped `__version__` to `0.18.0` with `x-release-please-version` marker
- Full suite: 792 passed, 4 skipped
- Confirmed: harness-owned session-start rectify rebakes generator stamp on version drift; `--version` is live from engine; `dev`-owned shim not touched by harness hooks

## Next Step
- QA phase (`niko-qa`), then open PR
