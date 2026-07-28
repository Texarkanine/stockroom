---
task_id: github-issue-and-pr-templates
date: 2026-07-28
complexity_level: 2
---

# Reflection: github-issue-and-pr-templates

## Summary

Shipped bug + feature GitHub issue forms (Area dropdown, blank issues + troubleshooting contact link) and a short PR template, pinned by packaging-style tests. Succeeded for #100/#101 launch-readiness.

## Requirements vs Outcome

Delivered: dual issue forms, blank issues enabled, ADHD-short prose with load-bearing fields (doctor-first bug form), PR conventional-commit/changelog checklist, no component-split forms. Added contact_links and title prefixes via preflight. Skipped CONTRIBUTING restatement (link only).

## Plan Accuracy

Plan held. Component-split correctly rejected after troubleshooting review. Main surprise was YAML placeholder quoting (`os: ...`), not design drift.

## Build & QA Observations

TDD red→green clean. QA only fixed CONTRIBUTING visibility in the PR template. Full `make ci` + `make docs-build` green.

## Insights

### Technical
- GitHub issue-form YAML treats unquoted values with `:` / `...` as structure; quote placeholders that look like mappings.

### Process
- Issue sketches as "ideas not gospel" + investigate field divergence before splitting templates avoided over-building.

### Million-Dollar Question

If templates had been assumed from day one: same shape — one bug form keyed on `stockroom doctor probe`, one short feature form, Area for routing, blanks for design docs. No separate component forms.
