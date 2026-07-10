---
task_id: dashboard-polish-m3-labels-and-help
date: 2026-07-10
complexity_level: 3
---

# Reflection: dashboard-polish-m3-labels-and-help

## Summary

Delivered friendly project labels with `project_id` on hover (#8) and clickable info-icon help for Session Efficiency and First-Prompt Quality (#7). Build and QA passed; operator amended the cwd-disagreement rule mid-flight to unique-short-name → full id.

## Requirements vs Outcome

- #8: `projects` stays ranked ids; parallel `labels`; chart/session/marathon hover only when display ≠ id — met.
- #7: info controls only on the two named panels; static `PANEL_HELP`; toggle/dismiss a11y — met.
- Grouping/ranking never switched to basename — met.
- No requirements dropped; the only reinterpretation was the locked cwd-pick decision (most-recent → unique short name), applied before implementation.

## Plan Accuracy

- File list and step order (metrics → panel model → adapter → help chrome → toggle) held.
- Preflight’s `_seed_session(cwd=)` and exact-assert `labels` notes were load-bearing and correct.
- Dirty WIP restore before step 1 prevented mixing trends/writeShare work into m3 — that challenge materialized as planned and was handled cleanly.
- Chart.js tick-hover limitation was correctly anticipated; tooltip-on-bar was the right surface.

## Creative Phase Review

No creative phase for this sub-run. Locked plan decisions (API shape, Chart.js tooltip, help UI) were sufficient and held up in code.

## Build & QA Observations

- TDD cycles were straightforward; projects-local cwd query avoided widening `_session_rows`.
- QA found only trivial DRY/KISS items (`PANEL_HELP` key alignment; reuse `project_display_name` in label helper) — no substantive gaps.
- `make ci` green at build end (485 pytest / 48 JS / ruff / REUSE).

## Cross-Phase Analysis

- Operator decision change landed in tasks.md before build; syncing test-plan wording avoided implementing the obsolete most-recent-cwd rule.
- Preflight’s TDD-encoding amendments made step-level test-before-code unambiguous and reduced QA surface.
- Leaving trends/writeShare WIP out of scope (and restoring it) was the highest-leverage plan item for keeping m2 contracts intact.

## Insights

### Technical
- Prefer projects-local metadata queries over widening shared `_session_rows` when only one endpoint needs extra columns — keeps overview/trends/efficiency signatures stable.
- When display names can collide or disagree, keep identity arrays (`projects` / `project_id`) authoritative and treat friendly strings as a parallel, nullable presentation layer (`labels` / `labelTitles`).

### Process
- Mid-plan operator amendments to locked decisions should rewrite dependent test-plan bullets in the same edit; otherwise build will faithfully implement the stale rule.
- Explicit “restore unrelated dirty WIP before step 1” belongs in the plan whenever the working tree carries out-of-scope contracts — it paid off here.
