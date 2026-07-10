---
task_id: fix-plugin-env-heal-after-move
date: 2026-07-10
complexity_level: 2
---

# Reflection: fix-plugin-env-heal-after-move

## Summary

Fixed plugin-root-move env staleness (#17): `ensure_engine_env` (torch-safe inexact sync) owned by shim/`rectify`, with stdlib hook bootstrap, shim duckdb refuse, and shared `ensure-env` for `sr-initialize`. Verified claims first; rejected the issue’s preferred shell-in-hooks approach.

## Requirements vs Outcome

Delivered: one hook cycle heals path + locked deps; no silent empty `.venv` on the on-path path; torch-safe rules preserved (heal never exact-syncs); Cursor/Claude share the same rectify→ensure contract. Did not claim `doctor smoke` without torch re-provision — correctly scoped to locked-deps/dashboard readiness.

## Plan Accuracy

Plan held. Preflight amendment (python3 bootstrap) was the right call — it removes the empty-venv chicken-egg the issue’s `[ -d .venv ]` recipe would miss. Fixture updates for duckdb-ready stub venvs were the main unplanned test churn.

## Build & QA Observations

TDD cycles were smooth; full suite stayed green. QA only needed doc/stderr polish. Live empty-venv → ensure-env → duckdb import confirmed the heal path outside unit stubs.

## Insights

### Technical
- `uv sync --frozen --check` is unsafe as a readiness probe when torch is present (it wants to uninstall torch); `--inexact --check` is the correct “locked deps OK?” signal.
- Hook `uv run --no-sync` against a missing project env creates an empty `.venv` before Python starts — any heal that keys only on directory presence is wrong.

### Process
- Verifying the issue’s claims and evaluating alternatives before coding paid off: the “preferred” fix would have duplicated untested shell and used a broken guard.

### Million-Dollar Question

If env readiness had been part of the shim contract from day one, `ensure_engine_env` would live beside render/install/rectify as the third heal primitive, hooks would always have used stdlib bootstrap, and `sr-initialize` would never have owned a one-liner sync. What we built is essentially that — retrofitted cleanly.
