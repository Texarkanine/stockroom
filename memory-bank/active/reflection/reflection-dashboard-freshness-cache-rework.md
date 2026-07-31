---
task_id: dashboard-freshness-cache
date: 2026-07-31
complexity_level: 1
---

# Reflection: dashboard-freshness-cache (efficiency rework)

## Summary

Stopped conversation-detail boot from faning out the metrics snapshot. Session deep-links now only load `/api/session`; server response cache from the L3 work remains for metrics home.

## What broke / fix

Boot always called `refreshDashboard(true)`. Gated with `shouldRefreshMetricsOnBoot` (false for valid `view=session` URLs).

## Insight

Caching unused work is worse than not requesting it — efficiency first, then cache what remains.
