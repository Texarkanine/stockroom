---
task_id: reuse-ppls-narrow-carveout
date: 2026-07-10
complexity_level: 2
---

# Reflection: reuse-ppls-narrow-carveout

## Summary

Inverted REUSE so PPL-S is a narrow carve-out (`SKILL.md` + `references/**`) instead of a blanket `skills/**` paint with AGPL claw-backs. SPDX before/after showed zero per-file license flips on the current tree; `make ci` stayed green.

## Requirements vs Outcome

All brief requirements delivered: targeted PPL-S globs, claw-back rules removed, Chart.js/`.cursor` kept, tests and systemPatterns updated, SPDX audit reported.

## Plan Accuracy

Plan matched execution. No surprises — the SPDX delta of zero flips confirmed the invert was expression-only for today's tracked files.

## Build & QA Observations

Clean build; QA found nothing to fix. Licensing tests already held under both paints for the overlapping contracts; the fixture-README AGPL assertion is the guard against a future `*.md` over-paint.

## Insights

### Technical
- For this repo's current `skills/` layout, broad-then-claw-back and narrow-carve-out resolve to identical SPDX license sets — the value of the invert is failure-mode direction (new software stays AGPL by default), not a license outcome change today.

### Process
- Nothing notable

### Million-Dollar Question

Starting from "AGPL base + PPL-S only on prompt payload paths" is what we shipped. The claw-back list was an artifact of painting the whole skill directory first; with the engine living under `skills/sr-search/`, the narrow carve-out is the natural expression.
