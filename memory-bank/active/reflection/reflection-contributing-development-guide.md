---
task_id: contributing-development-guide
date: 2026-07-12
complexity_level: 2
---

# Reflection: contributing-development-guide

## Summary

Reworked `docs/contributing/development.md` into a section-first day-to-day guide (prereqs, Make table, engine, Torch, docs site, dashboard, skills) assuming Local workflow setup; funnel pages and persistent MB pointers updated. Succeeded against the brief.

## Requirements vs Outcome

Delivered all requested surfaces in a sane order; Make table matched live `make help`; localdev enter/exit stayed in `local-workflow.md`. No descopes. Small additions within plan: intro jump list, funnel tweaks to `index.md` / `CONTRIBUTING.md`.

## Plan Accuracy

Plan sequence held. Challenges that mattered were the ones predicted (SSOT split, ensure-env vs `make torch`). No surprise touchpoints.

## Build & QA Observations

Build was a single rewrite plus light funnels; `docs-build` clean. QA only trivial polish (help row, HARNESS cell, ensure-env wording). Docs-only TDD via checklist worked once the “rip-it-out” pointer wasn’t treated as a second ritual.

## Insights

### Technical
- Contributor Torch docs should name `stockroom shim ensure-env` for restore; “heal” alone is too easy to confuse with `make torch`.

### Process
- After a large localdev docs task, finishing the paired Development page as L2 is the right cut — the ownership split is already decided.

### Million-Dollar Question

If Development had always been surface-first with Local workflow owning enter/exit, the Makefile dump would never have been the article. What we shipped is that foundational shape.
