# Active Context

## Current Task: fix-dashboard-utc-timestamps
**Phase:** PLAN - COMPLETE

## What Was Done
- Level 2 plan written for issue #32 UTC-at-rest / client-renders-zone contract
- Behaviors B1–B6 + edges mapped to ingest, migration watermark reset, metrics `Z` serialization, dashboard JS UTC parse
- Explicit non-goals: timestamptz migration; local peak-hour rebucket

## Next Step
- Preflight validation (automatic per Level 2 workflow)
