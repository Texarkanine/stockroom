# Progress

Stop the warehouse file growing far past the history it holds, as specified in [issue 147](https://github.com/Texarkanine/stockroom/issues/147) and `memory-bank/active/projectbrief.md`. Keep HNSW, rebuild it around embedding writes, insert vectors through NumPy, create new warehouses in the current DuckDB storage format with ZSTD text columns, rewrite an existing warehouse once in verify-only mode, and teach read-only `stockroom doctor` to report the file. The swap that replaces the live file stays a separate change and stays off.

**Complexity:** Level 4

## 2026-10-20 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Confirmed the issue is the spec, including the safety rules and the verify-only first release
    - Classified the work as Level 4
* Decisions made
    - Level 4 because the change crosses warehouse creation, embed writes, index lifetime, an automatic rewrite, and doctor, and a bad rewrite can lose the warehouse
    - Issue 147 supersedes the earlier creative note that dropped HNSW and added a `compact` command
* Insights
    - The approach is already decided in the issue. Planning only has to split it into milestones that can ship on their own

## 2026-10-20 - PLAN - COMPLETE

* Work completed
    - Split the issue into seven milestones in dependency order
    - Recorded the cross-milestone invariants, including verify-only as the default writer path
* Decisions made
    - New-file format and ZSTD: Level 2. One creation path, two column clauses, and one doc page
    - NumPy inserts: Level 2. One insert path in the embed writer
    - HNSW drop and recreate: Level 3. The growth bound, the skip-when-idle rule, and semantic search still answering
    - Doctor storage report: Level 2. Read-only facts on the existing probe
    - Verified copy: Level 3. Equality, catalog, HNSW, and every schema fixture, with the original untouched
    - Verify-only writer path: Level 3. Flock, skip rules, cleanup, and faults before any swap
    - Hard-link swap kept off: Level 3. The proof from the issue, without turning the default path into a replace
* Insights
    - Format, NumPy inserts, and the doctor report can start together. The HNSW wrap waits on the insert path. The copy waits on the new-file format. The swap waits on verify-only and on the doctor backup name

## 2026-10-20 - PREFLIGHT - COMPLETE

* Work completed
    - Validated Level 4 milestone decomposition in `memory-bank/active/milestones.md` against `projectbrief.md`
    - Confirmed serial-safety, DAG alignment, coverage, invariant constraints, and definitions of done across all 7 milestones
    - Recorded preflight status: PASS WITH ADVISORY
* Decisions made
    - Preflight result is PASS WITH ADVISORY. The milestone list was not changed
    - Advisory, not adopted: a verification receipt so verify-only mode does not rebuild on every later writer open, and so doctor can show that a copy already verified
* Insights
    - The 7-milestone decomposition cleanly separates read-only diagnostic visibility, incremental vector insert performance, index rebuild bounds, and non-destructive shadow verification from the final inactive swap operation

## 2026-10-20 - REVIEW - PLAN AMENDED

* Work completed
    - Measured `~/.local/share/stockroom/warehouse.duckdb`: 39.058 GiB, 159613 of 159982 blocks used, 369 free. Payload is 73 MiB of `messages.text`, 94 MiB of `tool_input`, and 192 MiB of vector floats. Counts match issue 147. This machine has about 806 GiB free. The work machine's 88 GB file was not opened
    - Amended the check-only milestone after the operator rejected a run on every writer open
* Decisions made
    - The check runs once, in the background. It records the result, deletes the temp file, and does not swap. Ingest and embed do not start it
    - The check-only release is how the work machine, which only receives stockroom through a release, proves its real warehouse before any swap
    - A later swap copies the warehouse again that day. Rows written after the check are only in the old file, and the old file stays in the old storage format
    - No periodic compaction. The HNSW drop-and-recreate stops the accumulation. The primary-key leak stays out of scope
    - Automatic deletion of a backup after a successful query was not adopted
* Insights
    - Preflight passed the writer-path wording and is stale for the amended check milestone. Re-preflight before building
    - The 88 GB collapse is an expectation from this machine's leak, not a measurement of that file

## 2026-10-20 - PREFLIGHT (RE-RUN) - COMPLETE

* Work completed
    - Re-validated the amended milestone list against `projectbrief.md`, issue 147, the operator's amendment, and the engine code
    - Recorded preflight status: FAIL (fixable)
* Decisions made
    - Prerequisites, checklist shape, coverage, scope, serial order, and done/risks blocks pass
    - Fixable: the background pass names no trigger, and every existing entry point is excluded. Scheduler entries reach a machine only on re-install. Session-start hooks need Cursor's third-party plugin setting and an engine entry point, which conflicts with "no new CLI command"
    - Fixable: "once" does not say which outcomes stand (terminal results versus skips and crashes that should retry)
    - Fixable: the verify-only milestone adds a doctor fact and the record doctor reads, but the invariants give milestone 4 sole ownership of reported facts. The DAG lacks the edge `doctor --> verifyonly`
    - Fixable: the brief calls issue 147 the authority, but the issue's writer-path trigger was overridden by the amendment
* Insights
    - Ingest's `write_session` also deletes embeddings, so it is a second writer that modifies the HNSW index. Milestone 3 has to cover it explicitly (advisory)
    - Radical advisory: a ledger of once-only maintenance jobs, launched from session start and read by doctor, would answer the trigger, once, and doctor-ownership findings together, and would make enabling the swap a single job registration

## 2026-10-20 - PLAN (RE-PLAN) - COMPLETE

* Work completed
    - Amended `milestones.md` and `projectbrief.md` for the four preflight findings. Still seven milestones
    - Milestone 6 is now "Run that copy once from the session-start hook in verify-only mode, and skip when the file is not ready"
    - Added the edges `doctor --> verifyonly` and `hnsw --> builder`. Dropped `doctor --> swap`, which the new edges imply
* Decisions made
    - Operator: the session-start hook starts the check as a hidden internal job. Not the nightly job, not a hand-run command. "No new CLI command" means no new user-facing command
    - Verified, mismatch, and already new are final. Each skip and a crash retry at the next session start. The record names a check version, so a later enabled swap runs under a new version
    - Milestone 6 owns the check record (a sidecar under the stockroom home) and one doctor line in the storage section milestone 4 built
    - Adopted advisories: milestone 3 picks how ingest's embedding deletes are handled, milestone 3 owns the index definition and milestone 5 reuses it, milestones 5 and 6 test with old-format files, the swap is a mode of the milestone 6 pass, and acceptance 5 now says the copy is verified and deleted, not swapped
    - Not adopted: a general job ledger. One check record with a version covers this project and the later swap
    - Issue 147 itself was not edited. The brief says where the amendments replace it
    - Advisory estimates: format L2, NumPy inserts L2, HNSW rebuild L3, doctor report L2, verified copy L3, session-start check L3, swap kept off L3
* Insights
    - Session-start hooks reach every machine with the plugin update, while nightly entries change only on re-install. That is why the hook is the only trigger that serves the check-only release

## 2026-10-20 - PREFLIGHT (THIRD RUN) - COMPLETE

* Work completed
    - Validated the re-planned milestone list against `projectbrief.md`, the engine code, and short DuckDB 1.5.4 experiments
    - Recorded preflight status: PASS WITH ADVISORY. The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. The four earlier fixable findings are resolved: trigger, once, doctor ownership, and brief authority
    - Advisory, not adopted: bound the pass's flock hold, because writers block on the flock with no time limit
    - Advisory, not adopted: name the "no warehouse" and "behind head" outcomes, hide or show the internal entry in `stockroom --help`, and have doctor open the warehouse without migrating
    - Radical advisory, not adopted: the check record stores measured sizes, times, and HNSW recall, and doctor prints them, so the swap is enabled from measurements on the work machine
* Insights
    - Measured: plain `COPY FROM DATABASE` gives `v1.5.0+` storage and copies the HNSW index, but text comes out `DICT_FSST`, not ZSTD. Milestone 5 has to create the tables from milestone 1's definition and copy `schema_version` rows verbatim
    - Measured: on an old-format file, `USING COMPRESSION zstd` gives no error and stores the column uncompressed. Connecting an existing file with the `latest` setting leaves it at `v1.0.0+`

## 2026-10-21 - REVIEW - PLAN AMENDED

* Work completed
    - Folded four third-run preflight advisories into `milestones.md` and `projectbrief.md`. Still seven milestones, same order and graph
* Decisions made
    - Operator adopted: a time limit on the pass's lock hold. An overrun deletes the temp file, releases the lock, and is a retrying skip
    - Operator adopted: milestone 5 attaches the copy in the new format, creates tables from milestone 1's definition, inserts rows, copies `schema_version` rows unchanged, and builds the index from milestone 3's definition
    - Operator adopted: no warehouse yet and a warehouse below the schema head are retrying skips
    - Operator adopted: the check is a measured rehearsal. Milestone 5's builder returns sizes, build and verification times, lowest free disk, and the index top-10 match share against an exact scan. Milestone 6 adds the lock-hold time to the record, and doctor's line prints them. The later swap release sets its margin and expected writer wait from these numbers
    - Operator declined: hiding the internal entry point from `stockroom --help`
    - Planner additions: the index match share is recorded, not a pass condition, and its exact scan must not use the index. A warehouse whose copy always overruns the time limit must not rebuild at every session start, and milestone 6's plan decides how
    - Doctor opening the warehouse without migrating is already required by "doctor never writes", so it was not added as a separate line
* Insights
    - The rehearsal turns the check-only release into the data source for the swap decision on the 88 GB work machine

## 2026-10-21 - PREFLIGHT (FOURTH RUN) - COMPLETE

* Work completed
    - Validated the 2026-10-21 amended milestone list against `projectbrief.md`, issue 147, the engine code, and short DuckDB 1.5.4 experiments
    - Recorded preflight status: PASS WITH ADVISORY. The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. Each new brief item (the measured rehearsal, the named skips, the cleanup after an overrun, and the doctor measurements) maps to milestone 5 or 6, and the builder's measurements have a handoff rule
    - Advisory, not adopted: requirement 4 says an overrun retries at the next session start, and milestone 6's risk says an always-overrunning copy must not rebuild at every session start. The two hold together only if "retry" means the pass runs again and decides whether to build. A crash that repeats has the same gap and leaves no record
    - Advisory, not adopted: milestone 4 owns a live-size estimate, which doctor's reclaimable figure and milestone 6's pre-build free-disk check both use
    - Advisory, not adopted: milestone 5's plan says where the head table definitions come from. Milestone 6 may split at the trigger
    - Radical advisory, not adopted: writers mark that they are waiting, and the pass yields to them, so the time limit only guards against hangs
* Insights
    - Measured: `con.interrupt()` does not stop `CREATE INDEX ... USING HNSW` during the build. An interrupt sent 10% into a 7.9 s build took effect 9.1 s later. The time limit needs a builder in a child process that can be killed
    - Measured: the HNSW leak sits in used blocks. A small file at 218.5 MiB had only 26.5 MiB free, so free blocks alone understate reclaimable space. Counting distinct `pragma_storage_info` blocks and adding `pragma_hnsw_index_info` works read-only
    - Measured: `ORDER BY array_cosine_distance(...) + 0 LIMIT 10` and a `row_number()` filter plan an exact scan, not `HNSW_INDEX_SCAN`

## 2026-10-21 - REVIEW - PLAN AMENDED (8 MILESTONES)

* Work completed
    - Folded fourth-run advisories 1 to 4 into the invariants and the milestone 4, 5, and 6 Done and Risks lines
    - Split milestone 6 at the trigger. Milestone 6 is the check itself (lock, child builder, time limit, skips, record, doctor line), and no shipped code starts it. Milestone 7 makes both session-start hooks launch it. The swap is now milestone 8
    - Graph: `builder --> check`, `doctor --> check`, `check --> hook`, `check --> swap`. The hook and the swap can run in parallel
* Decisions made
    - Operator adopted advisories 1 to 4 and the milestone 6 split. Operator declined the writer step-aside idea
    - Retry means the pass runs again and decides whether to build. After an overrun or a crash it rebuilds only under a condition milestone 6's plan chooses. A crash leaves a record that doctor shows
    - The builder runs in a child process. The parent holds the flock and kills the child at the time limit
    - Milestone 4 owns a live-size estimate. Doctor's reclaimable figure and milestone 6's low-disk test both use it
    - Milestone 5 runs the migrations on the empty copy, replaces `schema_version` rows with the original's, drops the index, inserts rows, and rebuilds the index from milestone 3's definition
    - Advisory estimates: format L2, NumPy inserts L2, HNSW rebuild L3, doctor report L2, verified copy L3, verify-only check L3, session-start hooks L2, swap kept off L3
* Insights
    - Advisories that only live in `progress.md` and `.preflight-status` are deleted when the first milestone finishes. Anything later milestones must see belongs in `milestones.md` or the brief

## 2026-10-21 - PREFLIGHT (FIFTH RUN) - COMPLETE

* Work completed
    - Validated the 8-milestone list against `projectbrief.md`, the diff from the fourth run's plan, the engine code, and short DuckDB 1.5.4 experiments
    - Recorded preflight status: PASS WITH ADVISORY. The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. The fourth run's five advisories are resolved in the plan. Milestone 6 owns the pass and milestone 7 owns the hook launch, with no overlap. The checklist is a valid serial walk of the new graph, and milestones 7 and 8 can run in parallel
    - Advisory, not adopted: only the flock holder writes the check record, written by temp file and `os.replace`. A busy skip from a concurrent session start must not replace a final result or an "attempt started" entry (milestone 6)
    - Advisory, not adopted: the check entry point detaches itself like `stockroom dashboard`, because Cursor's `sessionStart` does not redirect stderr (milestone 7)
    - Advisory, not adopted: milestone 7's plan says how "a session start after a final result does not build" is tested, because the hook tests check strings only
    - Advisory, not adopted: doctor checks the file through `resolve_home()` before `open_current()`, which creates the home folder, and still prints the facts that need no connection when the warehouse is missing, below head, or busy (milestone 4)
    - Radical advisory, not adopted: build the HNSW index on the temp file after the flock is released, and have the later swap check a fingerprint of the original under the flock. This replaces brief constraint 2
* Insights
    - Measured: `USING COMPRESSION zstd` survives a later `ALTER TABLE ... ADD COLUMN` (migration `0004` on `messages`) on a `v1.5.0+` file, so the clauses can live in `0001`
    - Measured: the original's inode, size, `mtime_ns`, and first 12 KiB stay the same through read-only and no-write opens, and change after an insert, an update, or a delete. A delete can keep the size the same
    - No migration seeds rows or rebuilds `messages` or `tool_calls`

