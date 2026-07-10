# Active Context

## Current Task: fix-plugin-env-heal-after-move
**Phase:** PLAN - COMPLETE (rework: hashed torch freeze)

## What Was Done
- Planned upgrade from index-only torch record to machine-local hashed freeze (`uv pip compile --generate-hashes`) after smoke; heal via `--require-hashes -r`.
- Validated compile live for `torch==2.7.1+cpu`.

## Next Step
- Preflight, then build.
