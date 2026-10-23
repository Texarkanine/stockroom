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

## 2026-10-22 - L4 PREFLIGHT - COMPLETE

* Work completed
    - Ran the Level 4 checks on the re-planned `milestones.md` against `projectbrief.md`: prerequisites, checklist shape, coverage, scope, order, invariants, and done and risks all pass
    - `.preflight-status` first line: `PASS WITH ADVISORY`. No plan edits were made
* Advisories (details in `.preflight-status`)
    - Requirement 10 and acceptance 11 cannot be met as worded, because `0001` and `0007` changed between v1.1.0 and v1.2.0 (comment-only `@rel` lines, #128). Milestone 3's target, the copy on `main`, can be met
    - The ERD generator reads `@rel` lines from every `*.sql` file in the migrations folder, so the schema file's name and folder matter. Future edges need a new home
    - Nothing enforces released-migration immutability. Use a purpose-built gate or review, not a change-detector test
    - Milestone 2's schema-1 migrate test contradicts milestone 3's stop rule
    - In a later release that adds `0010`, the check's "at the schema head" precondition and the runner's stop at the format boundary would deadlock. The check should key on a named boundary constant
    - Milestone 6's lasting-skip error state goes beyond brief requirement 3 and constraint 7. It needs an operator ruling or a creative phase, and the milestone may be worth splitting
    - The new-warehouse path never runs on real data before the release
    - Milestone 3's one-commit rule is stricter than needed
    - Radical innovation: one builder creates every warehouse file at a temp path, and a finished file is renamed into place
* Insights
    - DuckDB 2.0.0 applies forced zstd even to a 1-row table, and keeps it after a plain reopen and appends. So "already new" read from data segments works for every table that has rows

## 2026-10-22 - L4 REVIEW (OPERATOR) - COMPLETE

* Work completed
    - Folded the operator's review of the L4 preflight into `projectbrief.md` and `milestones.md`
* Decisions made (operator)
    - Comments in released migrations may be added or changed. Their SQL may not be changed to do something materially different. A gate in `make ci` and CI compares SQL with comments and whitespace removed against the latest release tag
    - Filesystems that refuse hard links are out of scope: APFS, Mac OS Extended (Journaled), ext4, and NTFS all support them. Milestone 6 drops that skip and the lasting-skip error state; a skip retries
    - Validate the new-warehouse path on real data in milestone 3. A new install must work when the project is done (brief acceptance 12, milestone 7)
    - Taken on the agent's judgment: the format-boundary constant as the check's precondition; milestone 2's schema-1 test becomes the stop test; temp-then-rename creation in milestone 3, extended by milestone 5; the commit order is relaxed; milestone 6 splits only if it classifies above Level 3
* Insights
    - The ERD's `@rel` comments (#128) already edited two released migrations. So the line the operator draws is SQL behaviour, not bytes
