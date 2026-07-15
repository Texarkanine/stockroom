---
task_id: surgical-embedding-invalidation
date: 2026-07-14
complexity_level: 2
---

# Reflection: Surgical embedding invalidation (#43)

## Summary

Implemented compare-and-keep embedding invalidation in the ingest writer so session rewrite deletes vectors only for removed or text-changed messages. Delivered as specified in issue #43; suite green.

## Requirements vs Outcome

All acceptance criteria met: unchanged/append retention, text-change and removal invalidation, other-session isolation, no schema migration, embed `NOT EXISTS`/`--full` untouched. No scope added beyond the preflight pure-helper amendment.

## Plan Accuracy

Plan sequence and file list held. No surprises in DuckDB or test fixtures; `UNNEST(?::VARCHAR[])` for stale owner ids worked on first try.

## Build & QA Observations

TDD red→green was clean (6 intentional fails, then all green). QA found no substantive issues.

## Insights

### Technical
- Blanket session cascade + ingest-then-embed lag is a latent semantic wipe: ingest deletes the index; failed embed never restores it. Surgical invalidation is lag resilience, not just re-embed cost savings.

### Process
- Nothing notable

### Million-Dollar Question

If surgical invalidation had been assumed from Phase 2, the writer would never have owned a session-wide embedding DELETE — invalidation would always have been compare-and-keep beside `first_seen_at` carry-forward, and the cascade creative option would not have shipped. What we built is that foundational shape; no further redesign needed.
