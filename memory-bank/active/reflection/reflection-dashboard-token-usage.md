---
task_id: dashboard-token-usage
date: 2026-07-22
complexity_level: 2
---

# Reflection: dashboard-token-usage

## Summary

Implemented dashboard token usage for [issue #83](https://github.com/Texarkanine/stockroom/issues/83): API join to `session_token_usage`, Tokens column on both lists, Model + Tokens on detail, via shared `dashboard-tokens.mjs`. Delivered as planned; full suite green.

## Requirements vs Outcome

All brief requirements landed: list column placement, compact K/M + hover breakdown, Claude zeros vs Cursor emdash (no hover), detail Model/Tokens without Session label, reusable mount. No scope creep beyond the operator's shared-component preference (already in the brief).

## Plan Accuracy

Plan sequence (API → shared module → list → detail → docs) held. Anticipated challenges (message-join multiplication, exact-equality test updates, hover vs panel-help) were the real ones; no mid-build replan.

## Build & QA Observations

Build was straightforward once the worktree synced deps. QA only needed a trivial DRY fix (`tokenBreakdownRows` once). Exact session-dict tests were the main mechanical touch surface.

## Insights

### Technical
- Dashboard session list enrichment already multiplies rows via LEFT JOIN messages; session-level fields (tokens) must be set once on setdefault, not per message row.

### Process
- Nothing notable

### Million-Dollar Question

If tokens had been a first-class dashboard assumption from day one, list/detail would have shared the same `tokens` payload shape and mount from the start — which is essentially what we added. No deeper redesign warranted.
