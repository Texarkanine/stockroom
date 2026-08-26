---
task_id: cursor-model-ingest
date: 2026-08-25
complexity_level: 2
---

# Reflection: cursor-model-ingest

## Summary

Cursor `sessions.models` after ~2026-08-20 were empty because the WSL enrichment walker aborted on a stale `/mnt/i` and never opened the live Windows `ai-code-tracking.db`. A fail-soft per-entry walk restores discovery. The tracking schema did not change.

## Requirements vs Outcome

Diagnosis, patch, and old-format compatibility all landed. Compatibility meant leaving `read_enrichment` SQL alone, not adding a second format. Already-written NULL rows still need one operator `stockroom ingest --full`.

## Plan Accuracy

The operator's schema-change guess was wrong; that was settled in planning, so the build never dual-read a new schema. File list and TDD order held. The real failure mode was exactly the one planned: an unguarded `is_dir()` / `iterdir()` on one `/mnt` child returning `[]`.

## Build & QA Observations

Red-then-green on the two abort cases; existing enrich/orchestrator tests stayed green. A live `load_enrichment` after the patch merged both DBs and attributed this session as `grok-4.6`. QA was docstring-only (`stated` → `statted`).

## Insights

### Technical

- Catching `OSError` around `Path.iterdir()` is not enough when the raise happens on a child's `is_dir()`. List names first (`os.listdir`), then stat each name.
- Transcript roots stay inside WSL `~/.cursor/`; model enrichment is the path that is supposed to merge `/mnt/<drive>/Users/*/.cursor/…`. Those are different surfaces.

### Process

- A cutoff that *looks* like a vendor schema change can be a discovery walk that died. Probe the live sidecar and `resolve_db_paths()` before planning a parser.

### Million-Dollar Question

The walker would have been fail-soft per entry from the start. Pins and `STOCKROOM_AI_TRACKING_DB` stay escape hatches, not the default. What we built is that assumption made explicit.
