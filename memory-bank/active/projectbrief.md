# Project Brief

## User Story

As a stockroom plugin user, I want session-start hooks to auto-heal after a marketplace plugin-hash move so that `stockroom` keeps working without a manual re-init.

## Use-Case(s)

### Use-Case 1

After Cursor/Claude updates the plugin to a new cache hash with no `.venv` in the new tree, one `sessionStart` / `SessionStart` cycle syncs deps, restores torch from the hashed freeze when present, rebakes `~/.local/bin/stockroom`, and leaves `stockroom --version` / dashboard launch working.

### Use-Case 2

With a dead baked `APP_DIR` and a missing new-tree `.venv`, the heal entrypoint still reaches `ensure_engine_env` instead of dying on `import duckdb` at module load.

## Requirements

1. Fix the chicken-and-egg where `python -m stockroom shim rectify` imports `duckdb` before `ensure_engine_env` can sync the new engine dir ([issue #25](https://github.com/Texarkanine/stockroom/issues/25)).
2. Prefer a dep-light heal import graph so `stockroom.shim` (and the heal stack) does not load DuckDB at import time.
3. Preserve torch restore from `{stockroom_home}/torch-requirements.txt` when a freeze exists; soft-fail when missing (no floating index heal).
4. Keep thin hooks; Python remains the single owner of heal policy.
5. Cover Cursor and Claude session-start bootstraps with packaging/hook tests.
6. Do not regress to premature `uv run --no-sync` that creates an empty `.venv`.

## Constraints

1. `uv python find` returns base CPython without locked deps — heal must not depend on that interpreter having site-packages.
2. `uv sync --frozen --inexact` alone does not install torch; torch still comes from `ensure_torch` / the hashed freeze.
3. Shared heal contract across Cursor and Claude hooks.
4. Follow TDD for all code changes.

## Acceptance Criteria

1. Delete `.venv` under the current plugin engine dir and point the shim at a dead hash; one Cursor `sessionStart` leaves `stockroom --version` working and `.venv` able to `import duckdb`.
2. Same for Claude `SessionStart`.
3. Torch restored from hashed freeze when present; soft-fail when freeze missing.
4. No silent empty `.venv` from premature `--no-sync`.
5. Packaging/hook tests cover the bootstrap that actually runs on both harnesses.
6. A test pins that importing `stockroom.shim` does not load `duckdb`.
