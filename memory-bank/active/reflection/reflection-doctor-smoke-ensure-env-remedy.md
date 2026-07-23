---
task_id: doctor-smoke-ensure-env-remedy
date: 2026-07-22
complexity_level: 2
---

# Reflection: doctor-smoke-ensure-env-remedy

## Summary

`doctor smoke`'s missing-torch errmsg now recommends `stockroom shim ensure-env` when `read_freeze_path()` finds a usable freeze, otherwise keeps the pip/`sr-initialize` remedy. Delivered to plan; tests and torch troubleshooting docs updated.

## Requirements vs Outcome

All acceptance criteria met. No scope additions beyond the planned torch.md bullet.

## Plan Accuracy

Plan held: touchpoints, freeze gate, CLI assertion branching, and TDD order (after preflight amendment) matched the build. No surprises beyond needing `make sync` in a fresh worktree before pytest.

## Build & QA Observations

Clean build; QA PASS with no fixes. Targeted red/green on the freeze-present unit test, then full suite.

## Insights

### Technical
- Smoke remedies should gate on the same freeze usability predicate as heal (`read_freeze_path`), not a looser "files exist" check — otherwise the errmsg can recommend a path that immediately soft-fails.

### Process
- Nothing notable

### Million-Dollar Question

If freeze-aware remedies had been assumed from the start, doctor would expose a tiny shared "next action for missing torch" helper used by smoke (and any future surfaces) rather than inlining the branch — what we built is the natural minimal form of that; extracting the helper now would be premature for a one-call site.
