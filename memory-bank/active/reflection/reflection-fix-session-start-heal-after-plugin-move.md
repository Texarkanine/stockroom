---
task_id: fix-session-start-heal-after-plugin-move
date: 2026-07-10
complexity_level: 2
---

# Reflection: fix-session-start-heal-after-plugin-move

## Summary

Closed the session-start heal chicken-and-egg from [issue #25](https://github.com/Texarkanine/stockroom/issues/25) by extracting DuckDB-free home resolution into `stockroom.home` so `shim rectify` can import on a bare `uv python find` interpreter. Hooks stayed thin; full suite green.

## Requirements vs Outcome

Delivered the preferred dep-light import-graph fix: heal reaches `ensure_engine_env` without DuckDB; torch soft-fail and packaging hook contracts unchanged. Live “delete `.venv` + dead hash” acceptance remains an operator smoke check on a real plugin cache — unit pins cover reachability and existing ensure/torch tests cover heal once imported.

## Plan Accuracy

Plan sequence and file list matched the build. No shell-sync hybrid needed. The only preflight amendment (pin dispatcher `shim --help` as well as bare import) was useful and cheap.

## Build & QA Observations

Red→green on import-graph tests was immediate once `torch_source` stopped importing `warehouse`. QA was clean — no debris or design rework.

## Insights

### Technical
- Heal-path import weight is a first-class contract: anything on the `shim` → `engine_env` → `torch_source` chain must stay free of warehouse/DuckDB (and similarly heavy) imports, or the next bootstrap tweak will re-break auto-heal.

### Process
- Nothing notable

### Million-Dollar Question

Home resolution would have lived in a stdlib-only module from the start, with warehouse importing it — not the other way around. That is essentially what we built; no larger redesign suggested.
