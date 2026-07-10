---
task_id: xdg-base-directory-layout
date: 2026-07-09
complexity_level: 3
---

# Reflection: xdg-base-directory-layout

## Summary

Shipped XDG data-home resolution for the warehouse tree (`STOCKROOM_HOME` override preserved), doctor `home` / `home-source` facts, and living-docs/O1 reconciliation — without legacy migration, per operator waiver of issue #3 migration items.

## Requirements vs Outcome

All accepted requirements landed: XDG default on *nix, override wins, dependents follow `home_dir()`, doctor reports source, docs/tests updated. Migration/conflict/legacy doctor facts were explicitly waived mid-plan and correctly did not ship.

## Plan Accuracy

The amended (post-waiver) plan matched the build. File list and TDD steps were right; the only plan amendment during preflight was pure `resolve_home()` so probe avoids mkdir — that held up cleanly. Pre-amendment creative/plan work around migration was largely throwaway once the operator waived it.

## Creative Phase Review

- **Q1 (layout shape)**: Single data-home tree (including logs) was the right call — zero schedule API churn, one operator story.
- **Q2 (legacy migration)**: Safe auto-migrate was explored and decided, then superseded by operator waiver. The creative doc remains as historical exploration; not implementing it was correct. Lesson: for private/low-install products, confirm whether issue acceptance checkboxes apply before deep design.

## Build & QA Observations

Build was straightforward (path constants + thin wrapper + probe facts + docs). Full suite green; QA found no debris. No substantive rework.

## Cross-Phase Analysis

Operator mid-cycle scope cut (drop migration) required re-preflight — the gate worked as designed. Preflight’s `resolve_home` advisory prevented a doctor side-effect that would have been easy to introduce by calling `home_dir()` from probe.

## Insights

### Technical
- Split “pure resolve + label” from “mkdir on use” is the right seam when diagnostics and writers share path policy: doctor stays side-effect-free while `home_dir()` remains the write-side chokepoint.

### Process
- When an issue’s acceptance includes migration but the operator has only private installs, pin that waiver in the project brief *before* creative — Q2’s auto-migrate exploration was high-quality and unused.
