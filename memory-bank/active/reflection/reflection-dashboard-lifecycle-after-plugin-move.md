---
task_id: dashboard-lifecycle-after-plugin-move
date: 2026-07-10
complexity_level: 2
---

# Reflection: dashboard-lifecycle-after-plugin-move

## Summary

Implemented start-time identity-aware dashboard replace so a healed engine after plugin move also replaces a stale owned listener on 6767 — without close hooks. Delivered to plan; suite green.

## Requirements vs Outcome

All brief requirements met: replace on stale owned identity, multi-harness safe (no stop-on-close), foreign listeners untouched, hook never-error, docs note for pre-identity one-shot manual kill. No scope creep.

## Plan Accuracy

Plan held. Preflight’s port-scoped identity amendment was the right call. Combining launcher decision matrix and foreground identity write in one pass was fine because tests still led. No surprise challenges beyond the accepted pre-identity gap.

## Build & QA Observations

TDD red→green was smooth. QA found only trivial test polish. `make sync` stripping torch during the full gate is a known footgun, unrelated to this change.

## Insights

### Technical
- Port probe alone is not identity; a durable home record (like torch freeze) is the right companion for disposable plugin trees.
- Only SIGTERM the pid we wrote, after cmdline verify — never hunt by port.

### Process
- Standing creative before `/niko` made L2 plan/build almost mechanical; keep that order for “last mile” reliability gaps after a related fix lands.

### Million-Dollar Question

If identity-aware replace had been assumed when the dashboard launcher was first designed, it would still be the same shape: probe → classify by home identity → reuse/replace/leave, with the OS bind as the spawn race mutex. Nothing more elegant emerged — close-hook lifecycle remains the wrong model for a machine singleton.
