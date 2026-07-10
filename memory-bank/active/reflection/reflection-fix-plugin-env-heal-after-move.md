---
task_id: fix-plugin-env-heal-after-move
date: 2026-07-10
complexity_level: 2
---

# Reflection: fix-plugin-env-heal-after-move

## Summary

Fixed plugin-root-move env staleness (#17): locked-deps heal via `ensure_engine_env`, plus durable torch-index under stockroom home so torch is reinstalled on rectify without re-picking a wheel.

## Requirements vs Outcome

First pass under-scoped torch (operator corrected). Rework delivers: `{stockroom_home}/torch-index`, `stockroom torch record`, heal in `ensure_engine_env`, writers in `sr-initialize` / `make torch`, hook timeout 300s.

## Plan Accuracy

Initial plan correctly rejected hook-shell sync and exact `--check`; wrong on “torch stays out of band forever.” Rework plan matched the real acceptance bar.

## Build & QA Observations

TDD for torch_source was clean. Existing installs need a one-time record before heal can restore torch.

## Insights

### Technical
- Torch heal requires state outside the disposable plugin tree; warehouse home is the right place.
- Inexact `--check` for deps + recorded index for torch is the full post-move contract.

### Process
- Operator pushback on “torch out of scope” was load-bearing — overnight embed failure mode is the real product break.

### Million-Dollar Question

From day one: `sr-initialize` would write torch-index, and rectify would always ensure deps+torch. What we have now is that contract, retrofitted.
