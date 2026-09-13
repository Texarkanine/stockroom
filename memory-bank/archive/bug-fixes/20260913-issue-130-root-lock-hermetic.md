---
task_id: issue-130-root-lock-hermetic
complexity_level: 1
date: 2026-09-13
status: completed
---

# TASK ARCHIVE: issue-130-root-lock-hermetic

## SUMMARY

The docs-only root `uv.lock` had ordinary packages (`certifi`, `jinja2`, `markupsafe`, `requests`, `urllib3`, and others) sourced from `https://download.pytorch.org/whl/cu126`. Regenerated with `uv lock --no-config --refresh` (same versions, PyPI sources). Contributor/CI paths now lock and run the docs toolchain hermetically. Ready PR: [#131](https://github.com/Texarkanine/stockroom/pull/131). Closes [#130](https://github.com/Texarkanine/stockroom/issues/130).

## REQUIREMENTS

1. Root `uv.lock` must not resolve ordinary packages from a PyTorch wheel registry.
2. Torch index stays on `uv pip install --index` / the stockroom-home freeze, not user-level uv config.
3. Installing Stockroom must not write a user-level uv `[[index]]` that other projects inherit.
4. Do not invent a global uv-config write that current HEAD did not already perform.

## IMPLEMENTATION

`--refresh` was required: `uv lock --locked` treated the contaminated lock as current because versions still satisfied the spec. `make lock` / `lock-check` now cover both uv projects; docs Make targets and docs CI pass `--no-config`; root lock-check uses `--locked --refresh --no-config`. Contributing docs and the root `pyproject.toml` header no longer instruct bare `uv lock` / `uv run` at repo root.

No `sr-initialize` or engine-runtime change. Torch index already writes a plain-text sidecar under stockroom home (`torch_source.write_index`), not `~/.config/uv`. The leak that shipped was inward (ambient extra index into the committed docs lock), not install rewriting other projects.

Key files: `uv.lock`, `skills/sr-search/tests/test_docs_lock_hermetic.py`, `Makefile`, `.github/workflows/docs.yaml`, `docs/contributing/iteration/docs.md`, `pyproject.toml`.

## TESTING

- TDD: `test_docs_lock_packages_are_pypi_with_hashes` failed on `certifi` from cu126; `test_docs_lock_is_not_stale` failed only after `--refresh` was added to the `uv lock --locked --no-config` invocation. Both passed after re-lock. `test_engine_source_does_not_write_user_uv_config` was already green.
- `make lock-check`, `make docs-build`, ruff, reuse lint clean.
- Engine pytest: 860 passed / 5 skipped; 4 failures pre-existing (Homebrew Node 26 vs required 22; `/tmp` vs `/private/tmp`). Dashboard JS 134 passed under Node 22.
- QA FAIL then PASS. First pass caught leftover `uv run properdocs serve --no-strict` without `--no-config`. Rework fixed that plus the `pyproject.toml` header comments.

## LESSONS LEARNED

`uv lock --locked` checks constraint satisfaction, not registry identity. A PyTorch extra index that is not `explicit = true` will pin common packages as well as torch. Contributor docs that say “just `uv lock`” at the repo root are a recurrence path. Plugin users and `sr-initialize` never consume the root docs lock.

## PROCESS IMPROVEMENTS

Level 1 has no archive phase; this document exists because the operator invoked `/niko-archive` after the L1 wrap-up. Root `uv run` can sync or resolve through ambient config the same way `uv lock` can — hermetic guidance must cover run, not only lock.

## TECHNICAL IMPROVEMENTS

QA advisories (non-blocking): the user-config scan duplicates `rglob` for `*.py` and `*.sh`; `make lock` re-locks engine and root even for a docs-only dep change. Engine `test_lock_is_not_stale` still omits `--refresh`; the engine lock is already PyPI-only via a separate assertion.

## NEXT STEPS

Land [#131](https://github.com/Texarkanine/stockroom/pull/131).
