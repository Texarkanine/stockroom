---
task_id: p4-dashboard-m3
date: 2026-07-09
complexity_level: 2
---

# Reflection: p4-dashboard / m3 — Launch surfaces

## Summary

Wired the existing dashboard launcher into the dispatcher, a thin `sr-dashboard` skill, and combined rectify-then-launch session-start hooks, and corrected planning ports to 6767. Delivered to plan; `make ci` green; manual smoke confirmed idempotent URL printing.

## Requirements vs Outcome

All m3 deliverables landed: `dashboard` in `SUBCOMMANDS`, `skills/sr-dashboard/SKILL.md`, one combined hook command per harness, roadmap/tech-brief port fixes. No descopes. One addition within plan intent: packaging asserts on-path launch is not folded into the rectify bootstrap, and a packaging contract for the port docs.

## Plan Accuracy

Sequence and file list were right. The chicken-egg challenge predicted in planning was the real design seam and was implemented as planned (plugin-root rectify, on-path dashboard). No reordering or surprise files. Skill hygiene briefly failed because negative guidance named forbidden tokens — a known trap, fixed by rephrasing.

## Build & QA Observations

Build was linear TDD with expected red→green cycles. QA found no code defects; it caught stale persistent docs (`systemPatterns` / `techContext` still described pre-m3 wrapper/hook/dispatcher surfaces) and fixed them in-phase. Manual smoke passed on the first try.

## Insights

### Technical
- Session-start heal cannot be “on-path only”: a dead baked `APP_DIR` makes `stockroom` itself unusable, so rectify must keep the plugin-root bootstrap while launch uses the healed shim.
- Wrapper-skill hygiene is a literal substring scan — even “don’t use PYTHONPATH” prose fails the test; phrase negatives without naming forbidden tokens.

### Process
- Soft “verify in build” steps for static docs are easy to under-test; a tiny packaging assertion (port 6767) closed that gap without new infrastructure.

### Million-Dollar Question

If launch surfaces had been assumed from day one of Phase 4, the dispatcher entry, `sr-dashboard`, and combined hook would still look like this — thin wiring over a complete launcher. The elegant form is what shipped: no second server entrypoint, no skill-side spawn logic, one silenced command per harness with structural idempotency (port bind).
