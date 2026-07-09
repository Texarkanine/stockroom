# Active Context

## Current Task: p4-dashboard / m3 — Launch surfaces
**Phase:** BUILD - COMPLETE

## What Was Done
- Registered `dashboard` in `stockroom.__main__.SUBCOMMANDS` and extended dispatcher tests.
- Added `skills/sr-dashboard/SKILL.md` and extended `WRAPPER_SKILLS` hygiene coverage.
- Combined rectify-then-launch into one session-start command per harness (`hooks/cursor-hooks.json`, `hooks/claude-hooks.json`); packaging asserts sequencing and on-path launch.
- Corrected planning ports 3143→6767 with a packaging contract.
- `make ci` green: 411 pytest passed / 3 skipped, 32 JS tests, ruff, REUSE.

## Files Modified
- `skills/sr-search/src/stockroom/__main__.py`
- `skills/sr-dashboard/SKILL.md` (new)
- `hooks/cursor-hooks.json`, `hooks/claude-hooks.json`
- `skills/sr-search/tests/test_dispatcher_cli.py`, `test_skill_hygiene.py`, `test_packaging.py`
- `planning/roadmap.md`, `planning/tech-brief.md`

## Next Step
- Run Level 2 QA.
