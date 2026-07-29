---
task_id: mature-pr-template-title-ci
date: 2026-07-28
complexity_level: 2
---

# Reflection: Mature PR Template + Title CI Check

## Summary

Shipped the Unautomatable-Only PR template (five prose sections, no checklist) and a dedicated conventional-commit title workflow; structural tests pin the contract without re-testing instructional prose.

## Requirements vs Outcome

All brief requirements met. CONTRIBUTING.md left unchanged by design. Template path stayed lowercase. Open PR is the remaining operator-facing deliverable after reflect.

## Plan Accuracy

Plan held. Dedicated `pr-title.yaml` was the right split from `ci.yml`. No surprises on REUSE (caught by `**/*` aggregate).

## Build & QA Observations

TDD red→green was clean. QA only simplified the types-assert helper and recorded the workflow in techContext — no substantive gaps.

## Insights

### Technical
- Nothing notable

### Process
- Once "don't put CI-checkable items in the template" is a hard constraint, the checklist dies entirely; the title check has to land in CI in the same change or the policy regresses to nothing.

### Million-Dollar Question

Nothing notable — a short template plus a title-lint job is what you'd design if conventional-commit titles and unautomatable author claims were assumed from day one.
