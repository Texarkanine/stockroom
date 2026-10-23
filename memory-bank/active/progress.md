# Progress

Stop the warehouse file growing far past the history it holds ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`). Milestones 1 (drop the HNSW index and `vss`) and 2 (DuckDB 2.0) are done. Re-planned on 2026-10-22 after the operator's rulings on migrations. Released migrations are restored as shipped. New warehouses come from a frozen version-9 schema file in DuckDB 2.0's format with zstd. A warehouse migrates or stops with an error. The copy-and-swap that moves old warehouses to the new format is durable. Milestones 1 to 3 make the first release.

**Complexity:** Level 4

## 2026-10-22 - RELEASE GATE (milestones 1 and 2) - COMPLETE

* Work completed
    - Tachi ran the personal Mac shadow test on Puck against `ce16489` (recorded in `ae39a67`). It used a fresh clone with `make sync`, no `--with`, and no `make shim`. The source was a 383,791,104-byte warehouse with no `.wal`
    - Exit 0, `shadow: every phase passed`. The copy stayed `v1.0.0+`, all six tables were equal, the schema was at the head, and there was no index
    - Ingest, embed, and semantic ran, DuckDB 1.5.4 wrote the copy, and 2.0.0 answered after that. No `nanobind` line. The live file's mtime was unchanged
* Decisions made
    - The work Mac stays out of the gate
* Insights
    - Puck's warehouse is 366 MB. The 88 GB work warehouse in `milestones.md` was not under test

## 2026-10-22 - L4 RE-PLAN - COMPLETE

* Work completed
    - Milestone 3's first Level 3 plan (`77dfeab`) put zstd into `0001` and had the runner drop the clause on old files. It passed preflight with advisory (`dd8e753`). The operator then ruled that released migrations may not be rewritten, which also covers milestone 1's edits to `0003`, `0001`'s comments, the `0003` to `0008` snapshots, and their tests on this branch. That plan is withdrawn. Its measurements, and its preflight's finding that `duckdb_tables().sql` shows `USING COMPRESSION ZSTD` on DuckDB 2.0.0, carry into milestone 3's and milestone 5's risks
    - Amended the brief (Migrations, Durability, releases, skipped releases, use cases, requirements 1, 2, and 10, acceptance 10 and 11)
    - Re-planned `milestones.md`: new invariants (Migrations, Migrate or stop, Durability), releases (milestones 1 to 3 together; Mac gate re-run after milestone 3), skipped-release arrivals (schema 3 to 8 migrate, below 3 stops), shared-artifact handoffs, milestone 3 rewritten, milestone 1 amended, milestone 5 builds from the schema file, and milestone 6 must not let a lasting skip leave a warehouse old in silence
    - Cleared milestone 3's sub-run files (`tasks.md` back to a stub, `.preflight-status` deleted) so `/niko` classifies milestone 3 fresh
* Decisions made (operator, 2026-10-22)
    - Released migrations are never edited, comments included. A runner rule that records a version without running it is rejected
    - One migration chain forever, plus a frozen schema file pinned to one version for new warehouses. A second chain for 2.0 and a declarative tool were each considered and dropped
    - A warehouse that cannot reach the head stops in an error state that users must resolve. No code copes with older states
    - Old-format warehouses may not persist. The copy-and-swap is the durable v1-to-v2 step of the chain
    - Milestone 3 joins the first release on this branch, replacing the separate-branch decision
* Milestone estimates (advisory)
    - Milestone 3: Level 3. It restores released files across migrations, snapshots, and tests; adds a schema file, the creation path, and an equality test; and changes fixtures and the shadow builder
    - Milestone 4: Level 3. The doctor storage report spans doctor, a live-size estimate, and a no-write guarantee
    - Milestone 5: Level 3. A verified copy with equality and catalog checks
    - Milestone 6: Level 3. Two phases, lock, time limit, fault injection, and lasting-skip handling
    - Milestone 7: Level 2. A detached launch from both hooks
* Insights
    - DuckDB sets compression only at `CREATE TABLE`, and a `v1.0.0` file cannot hold zstd at all. So compression for existing warehouses can come only from a new file, and for new warehouses only from what creates their tables
    - Restoring the released `0003` and adding the schema file must land together: either alone breaks new installs or edits released history
