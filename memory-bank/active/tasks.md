# Task: Trace ingest (ETL) — `p1-data-backbone-m3-trace-ingest`

**Complexity:** Level 3 (milestone 3 of the `p1-data-backbone` L4 project)

Incremental, per-source watermarked ETL that fills the migrated DuckDB warehouse from the operator's own Cursor and Claude Code history. Claude Code parsed clean-room from its native on-disk format; subagents linked to parents; kept content untruncated; tool inputs only; WSL/Windows-mount-aware path resolution; optional model/labeling enrichment from Cursor's `ai-code-tracking.db`. Built test-first through the milestone-2 `warehouse.open()` chokepoint over the milestone-1 schema.

> Stub created at COMPLEXITY-ANALYSIS. The Level 3 PLAN phase populates the checklists, component analysis, and TDD test plan below.
