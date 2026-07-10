---
task_id: fix-plugin-env-heal-after-move
date: 2026-07-10
complexity_level: 2
---

# Reflection: fix-plugin-env-heal-after-move

## Summary

Closed #17 env heal: locked-deps via `ensure_engine_env`, then hashed torch freeze under stockroom home so rectify restores the *same* torch bits (`--require-hashes`) after plugin moves — not a floating newer wheel from an index URL alone.

## Requirements vs Outcome

Three iterations: (1) deps-only heal under-scoped torch; (2) index-only record still allowed newer wheels on heal; (3) hashed freeze after smoke — delivered. Writers (`sr-initialize` install→smoke→freeze, `make torch`, CLI) and `docs/torch.md` match the operator contract. Legacy index-only homes must freeze once; no silent floating fallback.

## Plan Accuracy

Freeze plan matched build: compile with `--generate-hashes --emit-index-url`, heal from freeze only, remove `record`. Preflight amendments (default `--app-dir`, emit-index-url for heal resolve) were load-bearing and applied cleanly. No step reordering needed.

## Build & QA Observations

TDD steps stayed green with injectable runners (no network in unit tests). Full suite 456 passed / 3 skipped. QA clean aside from a Makefile comment polish; doctor’s floating install remedy correctly left as first-time provision (pre-freeze).

## Insights

### Technical
- Index URL alone is not a pin — heal must replay a hashed freeze or you silently drift past the smoke-accepted torch.
- Freeze also pins some PyPI transitives shared with `uv.lock`; install freeze after inexact sync and document the drift (acceptable).

### Process
- Operator “why” on floating heal was the right challenge: product break is overnight embed, not import-time convenience.

### Million-Dollar Question

From day one: initialize would smoke then freeze; rectify would always ensure deps + replay freeze. Same contract, fewer reworks.
