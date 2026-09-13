# Active Context

## Current Task: issue-130-root-lock-hermetic
**Phase:** BUILD - COMPLETE

## What Was Done
- Regenerated root `uv.lock` hermetically (`uv lock --no-config --refresh`); no `download.pytorch.org` sources remain; package versions unchanged.
- Added `test_docs_lock_hermetic.py`: PyPI+hashes, `uv lock --locked --refresh --no-config`, and a scan that install/torch paths do not mention `uv.toml` / `.config/uv`.
- `make lock` / `lock-check` now cover both uv projects; docs Makefile + docs CI use `--no-config`; docs CI also runs the hermetic lock check.
- Contributing docs no longer say bare `uv lock` at repo root.
- Verified: new tests green; engine pytest 860 passed / 5 skipped; 4 pre-existing env failures (Node 26 on PATH vs required 22; `/tmp` vs `/private/tmp` identity); dashboard JS 134 passed under Node 22; ruff, reuse, `make lock-check`, `make docs-build` clean.

## Next Step
- Level 1 QA via subagent (`/niko-qa`).
