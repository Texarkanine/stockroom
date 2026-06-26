# Progress

Milestone 3 of the `p1-data-backbone` L4 project: **Trace ingest (ETL)**. Build the incremental, per-source watermarked extract-transform-load that fills the migrated DuckDB warehouse from the operator's own history. Both harnesses: Cursor and Claude Code (Claude Code parsed clean-room from its native on-disk format). Watermarked per source (`last_mtime` / `last_path`) with a `--full` reset; subagents included and linked to their parent; kept content stored untruncated; tool inputs only (no outputs, no raw layer); WSL/Windows-mount-aware path resolution; optional model/labeling enrichment from Cursor's `ai-code-tracking.db` limited to model/labeling fields. Written test-first against real and pathological fixtures, through the milestone-2 `warehouse.open()` chokepoint and the milestone-1 locked schema, preserving the L4 cross-milestone invariants (no truncation at rest, harness-labeled single schema, tool-inputs-only, forward-only migrations, harness-neutral `~/.stockroom/` warehouse home, locked-uv trust, green `make ci` gate).

**Complexity:** Level 3

## 2026-06-25 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Re-entered `/niko` on the `p1-data-backbone` L4 project. Milestone 2 (Migration framework) was `REFLECT - COMPLETE`; checked it off in `milestones.md` and cleared its sub-run ephemeral files (`tasks.md`, `activeContext.md`, `progress.md`, `creative/`, `.qa-validation-status`, `.preflight-status`) per Step 2a.
    - Classified the next unchecked milestone (Trace ingest / ETL) as **Level 3**, matching the L4 plan/preflight advisory estimate.
    - Created fresh sub-run ephemeral files (this `progress.md`, stubbed `tasks.md`, refreshed `activeContext.md`); preserved the L4 `projectbrief.md`, `milestones.md`, and prior `reflection/` docs.
* Decisions made
    - L3, not L4: a complete feature across multiple cooperating components (two clean-room parsers, watermark state, WSL/mount-aware path resolution, subagent→parent linkage, optional enrichment) — but the overarching architecture is already fixed by the L4 plan and the now-built schema (m1) + migration framework (m2). This sub-run fills the existing warehouse through the existing `open()` chokepoint; it introduces no new architecture.
* Insights
    - The hard correctness claims (faithful untruncated capture, subagent linkage, harness generality) are exactly what the milestone says must be proven test-first against *real and pathological* fixtures — fixtures milestone 1 was tasked to commit as durable artifacts and that this milestone's ingest tests reuse.
