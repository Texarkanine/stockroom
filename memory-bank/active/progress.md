# Progress

L4 milestone 2 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse. The engine lock pins DuckDB 2.0 and the dependency range is `>=2.0,<2.1`; Dependabot ignores duckdb `>= 2.1.0` in the engine block. `scripts/shadow_duckdb_20.py` runs from a branch clone under a DuckDB 2.0 overlay against a copy of a real warehouse: it copies under the writer flock, checks equality after a 2.0 checkpoint, runs ingest and embed under 2.0, then has DuckDB 1.5.4 write to the copy, and 2.0 opens it after that. It exits 0 on this machine's warehouse before the 2.0 lock lands here. `docs/advanced/duckdb.md` states the 2.0 format and who can open it. `stockroom embed` and `stockroom semantic` print no nanobind leaked-instance warnings at exit under 2.0, unless the operator accepts them once the cause is known. The 2.0 lock is the last change this milestone brings into this checkout.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Checked off milestone 1 in `milestones.md` and cleared its sub-run files (its reflection stays in `reflection/`)
    - Classified milestone 2, "Move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse"
* Decisions made
    - Level 3, as the L4 re-plan estimated. The lock and dependency range, Dependabot, the rest of the shadow script and its tests, a live-copy run before the lock lands, a user-facing doc page, and the nanobind warnings (cause unknown) all change or need investigation. The commit hook syncs this checkout's environment to the working-tree lock, so the lock change is live on this machine at once

## 2026-10-22 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan in `tasks.md`: 7 steps and 11 behaviours (N1 to N5 for the Hub filter and the exit warning, S1 to S6 for the shadow script)
    - Probed the nanobind warnings on a DuckDB 2.0.0 overlay with torch installed from the hashed freeze (`scratchpad/m2/nanobind_probe*.py`)
    - Ran the full engine suite on a 2.0.0 overlay (1,040 passed, 38 skipped), resolved the 2.0 lock in a scratch copy, and checked the 2.0.0 wheels and the new-file tag
* Decisions made
    - Fix the nanobind warnings at their cause rather than ask the operator to accept them: `silence_unauthenticated_hub_warning` becomes a context manager around the model load
    - Pin 2.0.0, the only final 2.0 release; Dependabot ignores `>=2.1.0`
    - The 2.0 move is one commit (range, lock, Dependabot, doc page, techContext) after two gates: the full suite on a 2.0 overlay with torch, and the shadow run on a copy of the live warehouse. The shadow baseline stays as the rollback copy, and the first live 2.0 writes are supervised in the build, not left to 03:30
    - No pin test (change-detector). The shadow script fails on any nanobind line, so the operator's Mac runs check the fix there too
* Insights
    - The warning is not a DuckDB refcount bug in stockroom's queries: DuckDB with any binding, torch, and a plain sentence-transformers load are all clean. It is stockroom's own logger filter, which outlives the model load
    - A torch-free process cannot reproduce it, so only a torch-gated test can check the exit warning itself; a torch-free test checks the filter's scope
