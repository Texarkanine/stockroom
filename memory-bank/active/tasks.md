# Current Task: issue-130-root-lock-hermetic

**Complexity:** Level 1

## Fix

- **What broke:** Root `uv.lock` resolved ordinary docs packages (`certifi`, `requests`, `urllib3`, `jinja2`, `markupsafe`, …) from `https://download.pytorch.org/whl/cu126`.
- **Why:** Ambient user-level uv extra index participated in resolution. Contributing docs told maintainers to run bare `uv lock` at the repo root. `uv lock --locked` without `--refresh` treats a contaminated lock as current.
- **What changed:** Regenerated the root lock with `uv lock --no-config --refresh` (sources back to PyPI; versions unchanged). Hermetic lock tests for the docs lock. `make lock` / `lock-check` / docs targets and docs CI use `--no-config`; root lock-check uses `--refresh`. Contributing docs no longer instruct bare `uv lock`.
- **Install leak:** Engine `src/` and `scripts/` do not write `uv.toml` / `.config/uv`. Torch index stays on `--index` / stockroom-home freeze.

## Files

- `uv.lock`
- `skills/sr-search/tests/test_docs_lock_hermetic.py`
- `Makefile`
- `.github/workflows/docs.yaml`
- `docs/contributing/iteration/docs.md`
- `docs/contributing/iteration/index.md`
