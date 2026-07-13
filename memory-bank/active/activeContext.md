# Active Context

## Current Task: contributing-localdev-guide
**Phase:** PLAN - COMPLETE (rework²: atoms, no hook automation)

## What Was Done
- Dropped `local-hooks` and all hook-install automation from the plan.
- Rationale: committed hooks need `*_PLUGIN_ROOT`; unset after marketplace uninstall — copying `hooks/` into the project does not help.
- Docs will note manual hook work only when changing the bootstrap surface.

## Next Step
- `/niko-preflight` then `/niko-build`.
