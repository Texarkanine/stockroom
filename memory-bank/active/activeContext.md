# Active Context

## Current Task: contributing-localdev-guide
**Phase:** POST-REFLECT - polishing localdev UX (archive pending)

## What Was Done
- Post-reflect polish after rework² Reflect COMPLETE:
  - Enter path: drop blind `make torch`; heal via `ensure-env` / freeze.
  - `localdev-status` reports shim path, owner, app-dir, torch (not doctor pointer).
  - Fat Make recipes → `scripts/localdev.sh` (POSIX); Make orchestrates `skills`/`clean`/`status`.
  - `localdev-clean` unclaims `owner=dev` shim only; docs exit path = clean → reinstall plugin → launch → `sr-initialize` (rectify never creates).
  - Operator discussion open: should `shim rectify` create when dest absent?

## Next Step
- Decide/implement rectify-creates-when-absent (optional), then `/niko-archive` — or archive now and park rectify as a follow-up.
