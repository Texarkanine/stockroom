# Active Context

## Current Task: reuse-ppls-narrow-carveout
**Phase:** BUILD - COMPLETE

## What Was Done
- Updated `test_licensing.py` for inverted model (+ references PPL-S, fixture README AGPL)
- Narrowed `REUSE.toml` PPL-S to `SKILL.md` + `references/**`; dropped claw-back rules 3–4
- Updated `systemPatterns.md` layered-licensing blurb
- SPDX before/after: **0 license flips** on shared paths; 3 new AGPL memory-bank files only
- `make ci` green: 512 pytest passed / 3 skipped, 52 JS, ruff, reuse lint

## Next Step
- QA review

## Files modified
- `/home/mobaxterm/git/stockroom/REUSE.toml`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_licensing.py`
- `/home/mobaxterm/git/stockroom/memory-bank/systemPatterns.md`
