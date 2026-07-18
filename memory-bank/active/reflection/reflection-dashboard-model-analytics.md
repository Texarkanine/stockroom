---
task_id: dashboard-model-analytics
date: 2026-07-18
complexity_level: 3
---

# Reflection: dashboard-model-analytics

## Summary

Shipped dual-grain top-models (#67) and a conversation stacked-area model-over-time chart (#68) on the offline dashboard. Build and QA passed; operator layout amendments were absorbed without rearchitecting.

## Requirements vs Outcome

Delivered both grains as ranked bars, conversation-grain usage over time as one `panel-wide` area, sole-model Cursor message attribution, and clean-break `/api/models` + new `/api/model_trends`. No requirements dropped. Message-grain over-time was correctly descoped by operator amendment (ranking-only on the right). No docs change (user-guide has no panel list).

## Plan Accuracy

The 8-step TDD plan held. File list was right; challenge list (breaking shape, Cursor silence, color consistency, canvas pins) matched reality. Only naming tweak: attribution tests as `test_dashboard_model_usage.py` so `make test-dashboard-py` includes them. Preflight’s extraction of `model_usage.py` (skill_usage parallel) paid off.

## Creative Phase Review

- **Dual-grain attribution (B)**: Held up cleanly as pure helpers; metrics stayed thin. Sole-model fallback + multi-model skip behaved as designed in end-to-end tests.
- **Top-models (A)**: Two half-width bars with grain in titles — straightforward clone of the old bar builder.
- **Over-time (amended A)**: Single conversation area was simpler than the original two-area creative; operator amendment arrived before build, so no wasted implementation.

## Build & QA Observations

Build was smooth once attribution landed first. QA found one real issue: duplicated window SQL between `models()` and `model_trends()` — consolidated into `_model_attribution_inputs`. No completeness gaps.

## Cross-Phase Analysis

Operator layout amendment after preflight was the main mid-stream change; treating it as a plan amendment (not a rearchitect) kept preflight valid and avoided creative re-runs. Attribution-first ordering prevented bar/area divergence. Creative honesty about Cursor NULLs avoided “fixing” empty message charts later.

## Insights

### Technical
- When two metrics share grain rules, extract attribution before ranking/bucketing — the SQL load can also be shared once the pure helper exists.
- `make test-dashboard-py` globs `test_dashboard_*.py`; new dashboard test modules must match that prefix or they silently drop out of the slice.

### Process
- Operator visual amendments after preflight can stay plan amendments when they only change layout/grain presentation, not architecture — document and continue rather than re-preflight.
