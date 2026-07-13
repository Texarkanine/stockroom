# Active Context

## Current Task: contributing-localdev-guide
**Phase:** BUILD - COMPLETE (rework² thin atoms, no hook automation)

## What Was Done
- Deleted `hooks/localdev_hooks.py` + `tests/test_localdev_hooks.py`; stripped all Make hook install/clean/status.
- Makefile atoms: `require-harness`, `local-skills`, `local-engine`, `local-dashboard`, composer `localdev`, harness-scoped `localdev-clean`, slim `localdev-status`.
- Claude `local-skills` / `localdev-clean`: single-shell if/else (Make recipe-line pitfall fixed).
- Docs: rip-it-out + `HARNESS=… make localdev`; atom appendix; manual hooks/PLUGIN_ROOT footnote only.
- techContext + systemPatterns: atom composition, no PATH-hook install claim.
- Gates: shim pytest 29 + full ci 512 passed / 3 skipped; docs-build; M1–M9; B2/B3.

## Files modified
- `Makefile`
- `docs/contributing/local-workflow.md`, `development.md`
- `docs/user-guide/troubleshooting/index.md`
- `memory-bank/techContext.md`, `systemPatterns.md`, active MB
- Deleted: `hooks/localdev_hooks.py`, `skills/sr-search/tests/test_localdev_hooks.py`

## Deviations
- Fixed Claude early-`exit 0` Make pitfall (recipe lines are separate shells) — plan-compatible, not a plan change.

## Next Step
- `/niko-qa` (auto-transition)
