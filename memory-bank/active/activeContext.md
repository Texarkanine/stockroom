# Active Context

## Current Task: parallel-pytest-xdist
**Phase:** BUILD - COMPLETE

## What Was Done
- Locked `pytest-xdist~=3.0` (`3.8.0` + `execnet`); `addopts = ["-n", "auto"]` in engine pyproject.
- Contract tests in `test_lock_hermetic.py`; Make/CI unchanged (inherit addopts).
- `make test`: 586 pytest passed / 4 skipped (~19s, 16 workers); 86 JS; format/lint clean.
- Docs: `docs/contributing/iteration.md` + `memory-bank/techContext.md`.

## Files Modified
- `/home/mobaxterm/git/stockroom/skills/sr-search/pyproject.toml`
- `/home/mobaxterm/git/stockroom/skills/sr-search/uv.lock`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_lock_hermetic.py`
- `/home/mobaxterm/git/stockroom/docs/contributing/iteration.md`
- `/home/mobaxterm/git/stockroom/memory-bank/techContext.md`

## Key Decisions
- `addopts` is SSOT; no Makefile/CI `-n` duplication.
- No isolation fixes required under multi-worker run.

## Next Step
- QA review.
