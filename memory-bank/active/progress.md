# Progress

Determine whether Claude Code ingest overcounts token usage by storing each API response's usage on every content-block line, fix ingestion if that is a real bug, recompute sessions whose transcripts remain on disk, and rewrite vanished-transcript rows only when the correction is fully correct and idempotent.

**Complexity:** Level 2

## 2026-10-09 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated the investigation, the ingest fix, and the vanished-transcript bar; the operator approved it
    - Classified the work as Level 2
* Decisions made
    - Level 2: a bug fix across Claude ingest, message identity, the session token rollup, and a possible warehouse correction, without an architecture change
* Insights
    - The report's approximate collapse of consecutive assistant rows does not meet the operator's bar for rewriting rows whose transcripts are gone
