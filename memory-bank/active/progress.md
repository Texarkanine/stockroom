# Progress

Phase 2 makes the faithful warehouse content findable by meaning: an embedding
pipeline (local `sentence-transformers`, `FLOAT[384]`, DuckDB VSS/HNSW cosine
index, GPU-or-CPU, incremental re-embed) and two read surfaces — `sr-semantic`
(pure vector search) and `sr-search` (blended keyword + semantic with
context-aware read-time truncation). Built on the Phase 0 torch contract and the
Phase 1 warehouse/chokepoint. Executed as a Level 4 project: a milestone list of
independently deliverable L1/L2/L3 sub-runs.

**Complexity:** Level 4

## 2026-06-28 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Classified Phase 2 as Level 4 (Complex System), consistent with the archived Phase 1 L4 pattern.
    - Wrote the ephemeral memory-bank files (projectbrief, activeContext, tasks, this progress file).
* Decisions made
    - Each roadmap Phase is an L4 system; Phase 2 decomposes into milestone sub-runs.
    - Task ID: `p2-embeddings-search`.
* Insights
    - The `embeddings` table is already forward-declared in `0001`; Phase 2's schema work is the deferred VSS/HNSW index, which lands as a new forward-only migration.

## 2026-06-28 - PLAN - COMPLETE

* Work completed
    - Generated `memory-bank/active/milestones.md`: 3 milestones (embedding pipeline, `sr-semantic`, `sr-search`), strictly sequential.
    - Recorded cross-milestone invariants and advisory L-estimates (L3/L2/L3) with rationale, plus open questions for sub-run creative phases.
* Decisions made
    - Followed the roadmap's 3-milestone decomposition rather than splitting (e.g., the VSS index migration stays bundled into the embedding-pipeline milestone, per the roadmap; flagged as a preflight consideration).
    - No dependency flowchart: all milestones are sequential.
* Insights
    - Surface packaging (engine module vs. polished skill wrapper) should follow the Phase 1 `sr-query` precedent — wrapper deferred to Phase 5.

## 2026-06-28 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the milestone list against codebase reality: PASS (with advisory).
    - Confirmed three findings against the repo: CI is torch-free (`ci.yml`), no existing VSS/embedding code, and existing tests are coupled to the migration head/snapshot.
    - Recorded binding sub-run findings + a load-bearing-primitive spike directive in `milestones.md`; wrote `.preflight-status`.
* Decisions made
    - Folded one in-scope improvement into the plan (the m1 spike directive); flagged the rest as advisories for the m1 sub-run rather than rearchitecting.
    - No FAIL: per-unit TDD ordering correctly lives in each sub-run, not the L4 milestone list.
* Insights
    - The dominant Phase-2 risks are torch-in-CI testability and VSS-extension provisioning under the offline posture — both belong to m1 and both are de-risked cheaply by an upfront probe (the Phase-1 "spike the primitive" lesson).


