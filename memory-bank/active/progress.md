# Progress

L4 milestone 2 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse. The engine lock pins DuckDB 2.0 and the dependency range is `>=2.0,<2.1`; Dependabot ignores duckdb `>= 2.1.0` in the engine block. `scripts/shadow_duckdb_20.py` runs from a branch clone under a DuckDB 2.0 overlay against a copy of a real warehouse: it copies under the writer flock, checks equality after a 2.0 checkpoint, runs ingest and embed under 2.0, then has DuckDB 1.5.4 write to the copy, and 2.0 opens it after that. It exits 0 on this machine's warehouse before the 2.0 lock lands here. `docs/advanced/duckdb.md` states the 2.0 format and who can open it. `stockroom embed` and `stockroom semantic` print no nanobind leaked-instance warnings at exit under 2.0, unless the operator accepts them once the cause is known. The 2.0 lock is the last change this milestone brings into this checkout.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Checked off milestone 1 in `milestones.md` and cleared its sub-run files (its reflection stays in `reflection/`)
    - Classified milestone 2, "Move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse"
* Decisions made
    - Level 3, as the L4 re-plan estimated. The lock and dependency range, Dependabot, the rest of the shadow script and its tests, a live-copy run before the lock lands, a user-facing doc page, and the nanobind warnings (cause unknown) all change or need investigation. The commit hook syncs this checkout's environment to the working-tree lock, so the lock change is live on this machine at once
