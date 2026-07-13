---
task_id: contributing-localdev-guide
date: 2026-07-12
complexity_level: 3
---

# Reflection: contributing-localdev-guide (rework²)

## Summary

Delivered thin Makefile atoms (`local-skills`, `local-engine`, `local-dashboard` + composer `localdev`) with required `HARNESS`, deleted project-hook automation, and rewrote Contributing for rip-it-out + modular appendix. Succeeded against the binding rework² plan after nk-refresh threw out the mega-recipe.

## Requirements vs Outcome

Met: rip-it-out docs, delete `plugin-local` (already gone), shim FORCE (already green), thin atoms + `HARNESS`, no Make hook install, `localdev-clean`/`status` semantics, manual PLUGIN_ROOT footnote. Nothing descoped. No extras beyond the Make recipe-line fix for Claude branches.

## Plan Accuracy

Rework² plan (atoms inventory + M3–M9 + delete helper) matched the tree. Preflight’s check-fail→implement amendment kept TDD honest. The surprise was operational, not planning: Make’s one-shell-per-line made Claude’s early `exit 0` a no-op — caught during build verification, not by the plan.

## Creative Phase Review

FORCE two-key held. Composition amendment (atoms + `HARNESS`) held. Hooks *automation* (creative Option B) did **not** hold once PLUGIN_ROOT-after-uninstall was understood — operator + nk-refresh correctly superseded it; build ignored stale creative install notes per preflight. PATH-based hook *content* remains a valid manual pattern only.

## Build & QA Observations

Build was mostly mechanical once atoms were clear. Full `make ci` and docs-build stayed green. QA found no substantive drift — only a stale projectbrief constraint line about “hooks-in-localdev.”

## Cross-Phase Analysis

nk-refresh during the interrupted mega-`localdev` build was the high-leverage intervention: it prevented shipping over-automation that matched the letter of an earlier rework §4 but violated the first creative’s anti-mega-enter principle. Preflight’s “ignore stale creative Hooks notes” amendment prevented build from re-introducing deleted automation from creative Implementation Notes.

## Insights

### Technical
- Make recipe lines are separate shells; harness branching must be one compound `if/else`, not `exit 0` then more lines.
- Copying `hooks/*.json` into a project cannot fix missing `*_PLUGIN_ROOT` after marketplace uninstall — automation cannot paper over that.

### Process
- “One-shot for the operator” must mean a thin composer, not one opaque recipe body — nk-refresh should fire when enter path grows side effects without named atoms.
- When creative Implementation Notes diverge from a later operator amendment, preflight must name the binding text explicitly or build will resurrect dead design.
