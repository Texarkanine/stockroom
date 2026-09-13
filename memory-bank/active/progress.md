# Progress

Regenerate the docs-only root `uv.lock` without a PyTorch wheel registry, and confirm Stockroom install does not write user-level uv extra indexes that bleed into other projects.

**Complexity:** Level 1

## 2026-09-13 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed operator intent against [issue #130](https://github.com/Texarkanine/stockroom/issues/130)
    - Recorded additional constraint: Stockroom install must not leak into other projects' uv configs
    - Classified as Level 1
* Decisions made
    - Level 1: bug fix, single concern (root lock hermeticity + no global uv-index write)
    - Not L2: no new feature or multi-subsystem design; leftover installer writes are a check, not an architecture change
* Insights
    - Issue investigation already found current torch paths use `--no-config` and do not instruct a user-level `[[index]]`; the committed root lock is the proven defect

## 2026-09-13 - COMPLEXITY-ANALYSIS - COMPLETE (leaving for BUILD)

* Work completed
    - Memory-bank ephemeral files written; ready to enter Build
* Decisions made
    - L1 skips plan/creative/preflight; next phase is Build

## 2026-09-13 - BUILD - COMPLETE

* Work completed
    - Regenerated root `uv.lock` with `uv lock --no-config --refresh`
    - Added docs-lock hermeticity tests
    - Wired `--no-config` (and root `--refresh`) into Make + docs CI
    - Fixed contributing docs that instructed bare `uv lock`
* Decisions made
    - `--refresh` not `--upgrade`: same versions, PyPI sources only
    - `uv lock --locked` without `--refresh` is a false green on extra-index contamination
    - No user-level `[[index]]` write existed; pin that with a source scan rather than inventing a config write
* Insights
    - `--locked` checks constraint satisfaction, not registry identity
    - `docs/contributing/iteration/docs.md` was the recurrence path

## 2026-09-13 - BUILD - COMPLETE (leaving for QA)

* Work completed
    - Ready for Level 1 QA subagent

## 2026-09-13 - QA - COMPLETE (FAIL)

* Work completed
    - Reviewed the committed change set against the task brief and hermeticity requirements
    - Confirmed no root-lock package uses the PyTorch registry
    - Ran `test_docs_lock_hermetic.py` successfully (3 passed)
* Decisions made
    - Build must rerun to correct the remaining bare root `uv run` command in docs guidance
* Insights
    - `uv run` can resolve or sync dependencies; root contributor commands need `--no-config` just like lock and sync commands

## 2026-09-13 - BUILD - COMPLETE (QA rework)

* Work completed
    - Non-strict docs preview command now includes `--no-config`
    - Root `pyproject.toml` header comments match the hermetic invocations
    - Contributing docs now forbid bare `uv run` at repo root as well as `uv lock` / `uv add`
* Decisions made
    - Same class as the QA finding: every root uv invocation in contributor-facing guidance gets `--no-config`
