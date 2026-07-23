---
task_id: cursor-ai-tracking-multi-db
date: 2026-07-22
complexity_level: 2
---

# Reflection: cursor-ai-tracking-multi-db

## Summary

Fixed [#82](https://github.com/Texarkanine/stockroom/issues/82) by walking/merging all readable Cursor `ai-code-tracking.db` candidates (plus additive XDG `ai_tracking_dbs`), keeping single-DB env/kwarg overrides. Delivered on `wsl-dual-sot` without reviving aborted `state.vscdb` enrich.

## Requirements vs Outcome

All acceptance criteria met: multi-DB merge under default ingest, additive fail-soft pins, re-ingest no longer wiped by WSL shadow DB, docs + tests. Out-of-scope items (vscdb tokens, Claude tokens, #84) stayed out. Residual “preserve models on total enrich miss” remains a separate integrity question, not this fix.

## Plan Accuracy

Plan sequence held: config home → settings → resolve set → merge → orchestrator → docs. Preflight’s TDD-encoding amendment and orchestrator AC test were the right gates — unit helpers alone would have looked green while ingest stayed first-hit.

## Build & QA Observations

Build was smooth; monkeypatch needed `from stockroom import config` (not a bound import). Full suite green (671/1). QA only found a small DRY smell in `default_db_path` re-checking env.

## Insights

### Technical
- First-hit path resolution is a silent dual-corpus footgun whenever writers land disjoint ID spaces under ordered candidates — prefer walk/merge (or explicit multi-source) for optional sidecars, and reserve env for true single-source overrides.

### Process
- Preflight should keep treating “helpers updated, orchestrator seam unchanged” as a plan-failure mode; the AC-level orchestrator test belonged in the plan from the start.

### Million-Dollar Question

If multi-source ai-tracking had been assumed from day one, enrich would expose only `load_enrichment()` / `resolve_db_paths()` with env as a singleton override — no first-hit `default_db_path` as the primary API. What we shipped is that shape with a thin diagnostic leftover; good enough.
