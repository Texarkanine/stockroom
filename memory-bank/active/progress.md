# Progress

Add nullable `sessions.workspace_key` with extensible per-harness ETL transforms so same-cwd cross-harness sessions share a queryable rollup key; wire Sessions by Project to that key; document the contract.

**Complexity:** Level 3

## 2026-07-14 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent restatement approved (including per-harness T extensibility)
    - Ephemeral memory-bank files created; prior creative retained
    - Complexity classified as Level 3
* Decisions made
    - Level 3: schema + ingest strategies + metrics + docs (multiple components)
    - Creative already done standalone — plan should treat rollup-layer questions as resolved
* Insights
    - Column name `workspace_key`; convergence on same cwd/machine; identity `project_id` unchanged

## 2026-07-14 - PLAN - COMPLETE

* Work completed
    - Component analysis, test plan, implementation steps, challenges, pre-mortem
    - Branched `feat/workspace-key` from main
* Decisions made
    - metrics groups by `coalesce(workspace_key, project_id)`; column itself stays NULL when underivable
    - `projects[]` API values are rollup keys
    - Migration `0006_workspace_key.sql`; no DML backfill
* Insights
    - Existing basename-collide metrics test must be reinterpreted under workspace_key semantics

## 2026-07-14 - PREFLIGHT - COMPLETE (PASS)

* Work completed
    - Validated TDD encoding, conventions, dependency blast radius (incl. migrate_runner head pins)
    - Amended plan for `test_migrate_runner.py` 5→6
* Decisions made
    - Preflight PASS; Build awaits `/niko-build`
* Insights
    - Advisory only: optional multi-`project_id` hover list out of scope

## 2026-07-14 - BUILD - COMPLETE

* Work completed
    - `workspace_key_for` harness registry; migration 0006; model/writer/golden; metrics rollup; docs
    - Full `make test` green (524 passed, 3 skipped; dashboard JS 61)
* Decisions made
    - Writer always computes key at insert; metrics groups by `coalesce(workspace_key, project_id)`
    - Head pins also updated in warehouse open/concurrency tests + locked snapshot → 0006
* Insights
    - Preflight’s migrate_runner-only head note under-scoped warehouse open/concurrency pins
