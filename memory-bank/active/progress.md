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

## 2026-10-21 - REVIEW - PLAN AMENDED (FIFTH-RUN ADVISORIES)

* Work completed
    - Folded fifth-run advisories 1 to 4 into the milestone 4, 6, and 7 Done and Risks lines, and into the hook milestone's shared-artifact rule. Still eight milestones, same order and graph
* Decisions made
    - Operator adopted advisories 1 to 4 and asked for one more preflight. Operator declined the index-after-unlock idea, so brief constraint 2 stands
    - Milestone 6: only the lock holder writes the check record, through a temp file and a rename. A busy-lock skip writes nothing
    - Milestone 7: the launch detaches the way `stockroom dashboard` does, and milestone 7 owns that detached launch. A test runs the entry point against a final record to prove no build
    - Milestone 4: doctor checks that the file exists before opening anything, never creates the stockroom home, and still prints connection-free facts when the warehouse is missing, below head, or busy
* Insights
    - Confirmed in code: `open_current()` reaches `home_dir()`, which runs `mkdir`. Doctor's probe already uses the pure `resolve_home()`
    - Confirmed in code: Cursor's session-start hook redirects stdout only. Claude Code's redirects both streams

## 2026-10-21 - REVIEW - SHORT-LIVED LENS APPLIED

* Work completed
    - The sixth preflight run was aborted before it wrote anything
    - Pinned the operator's lifetime statement first in the `milestones.md` invariants and in the brief: milestones 5 to 8 are a short-lived migration utility for about five or six installs, kept a month or two, then removed
    - Simplified the chain under that lens. Still eight milestones, same order and graph
* Decisions made
    - A crash or a time-limit overrun is now final. Its started entry stays for doctor, and deleting the record file retries. This replaces "rebuild only under a condition the plan chooses"
    - The time limit ends the pass's own process (for example `signal.alarm` with its default action), and the OS releases the flock. No child builder process
    - The rehearsal keeps the original's size, the copy's size, free disk at the start, and the build, verification, and lock-hold times. Dropped: lowest free disk during the run, and the index top-10 match share against an exact scan
    - One old-format fixture with rows at `0001` and at head replaces fixtures at every schema version
    - The chain lives in its own module, touching shared code only at its entry point, the hook command, and doctor's check and backup lines, so removing it is a deletion
    - Unchanged on purpose: every data-safety rule, fault-injection and SHA-256 proofs, the lock-holder-only record write, the detached launch, and milestones 1 to 4
* Insights
    - Data-safety rules are the only part of the chain that must not shrink with its lifetime

## 2026-10-21 - PREFLIGHT (SIXTH RUN) - COMPLETE

* Work completed
    - Validated the 8-milestone list after the fifth-run advisories and the short-lived lens, against `projectbrief.md`, the diff from `beb1abe`, the engine code, and one DuckDB 1.5.4 experiment
    - Recorded preflight status: PASS WITH ADVISORY. The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. Every lens change maps to a milestone, the graph is unchanged, and no wording from the earlier design is left
    - Advisory, not adopted: a pass takes the flock before it reads the record or deletes anything. A started entry is now final, so without this a second session start can delete the temp file of a pass that is still running (milestones 6 and 8)
    - Advisory, not adopted: the started entry carries its start time and the time limit, so doctor can tell a running pass from a dead one. Doctor names the record path, because deleting it is the only retry (milestone 6)
    - Advisory, not adopted: set the alarm only in the entry point's process, not in the pass function that in-process tests call under `pytest-xdist` (milestone 6)
    - Advisory, not adopted: doctor's backup line is durable, not chain code that removal deletes, because a 39 to 88 GB backup can outlive the chain (invariants, milestone 4)
    - Radical advisory, not adopted: turn on the swap per machine with a config key instead of a release, so each machine swaps on its own rehearsal numbers
* Insights
    - Measured: `signal.alarm` with its default action ended a process 2.03 s into a 10.4 s HNSW build (exit -14), and a blocked flock waiter got the lock at that moment
    - No engine code installs a signal handler, and the test stack has no timeout plugin

## 2026-10-21 - REVIEW - POST-PREFLIGHT FIXES

* Work completed
    - Folded sixth-run advisories 1 to 4 into milestone 6, the lifetime paragraph, and brief constraint 8. No re-preflight: each is a one-sentence correction to the lens edits and changes no milestone's scope, order, or ownership
* Decisions made
    - Every pass takes the lock without waiting before it reads the record or deletes anything. A pass that cannot take it does nothing, so it cannot delete a running pass's temp file
    - The started entry carries its start time and time limit. Doctor shows one inside its limit as running, and prints the record's path because deleting it is the retry
    - Only the entry point's own process sets the alarm, so in-process tests cannot kill an xdist worker
    - Doctor's backup line outlives the chain's removal
    - Not adopted: a per-machine `config.toml` key to enable the swap. That is the operator's call and would change the brief's "later explicit change"
* Insights
    - Making crashes final made a running pass and a dead pass look alike. Lock-first ordering is what keeps them apart


## 2026-10-21 - REVIEW - PLAN AMENDED (DUCKDB 2.0 FIRST, SKIPPED RELEASES)

* Work completed
    - `/niko` had classified the format milestone as a Level 2 sub-run (commit `ce2e784`). That classification is withdrawn: the operator inserted a new first milestone, so `progress.md` and `tasks.md` were restored to the Level 4 plan state
    - Probed the format milestone on DuckDB 1.5.4 (`.scratch/scripts/m1_new_file_probe.py`): a new file under `storage_compatibility_version = 'latest'` is `v1.5.0+` with ZSTD on both columns; the setting leaves an existing `v1.0.0+` file's tag and codecs unchanged; two read-write connections to one file in one process must carry the same config; DuckDB 1.4.5 cannot read a `v1.5.0+` file
    - Probed DuckDB 2.0.0 (released 2026-10-21) and 1.5.6: 2.0 creates `v2.0.0+` files even without the setting, reads `v1.0.0+` and `v1.5.0+` files, installs vss, still plans top-k through HNSW (EXPLAIN prints `Hnsw Index Scan`), and gives ZSTD for the clauses. The engine suite passes unchanged on 2.0.0 (1024 passed, 38 skipped, torch absent). No shipped SQL uses the single-arrow lambda syntax 2.0 turns off
    - Every stockroom release tag (v0.1.0 to v2.1.2) and every lock in the repo's history pinned DuckDB 1.5.4. This machine's live warehouse is `v1.0.0+` at schema version 8
    - Amended `milestones.md` (now 9 milestones) and `projectbrief.md`
* Decisions made
    - Operator: move the engine to DuckDB 2.0 (LTS until at least October 2027) as the new first milestone, released on its own before the copy chain, so the one-time rewrite targets the format stockroom keeps
    - Operator: every release must stand alone. Users skip releases, so no milestone may assume that a user ran an earlier release of this project, the check, or the swap. The arrivals each release must handle: a `v1.0.0+` file at schema versions 1 to 8, a `v2.0.0+` file with or without zstd columns and leaked index copies, and no warehouse
    - The 2.0 milestone owns the pin and the user-facing statement of which DuckDB versions open the warehouse. It shadow-tests a copy of this machine's real warehouse, proves a schema-1 `v1.0.0+` warehouse migrates to head under 2.0, and re-measures every 1.5.4 fact that later milestones and `docs/architecture/embeddings.md` state. A premise that no longer holds stops for the operator
    - Format milestone: the new-file tag follows the pinned DuckDB (`v2.0.0+`), set explicitly at creation. Its plan chooses `'latest'` or an explicit 2.0 storage version. Its doc line moved to the 2.0 milestone
    - Copy milestone: one `v1.0.0+` fixture at head is enough because the check copies only a warehouse at head. The earlier reason ("every real install is at head") does not hold once releases are skipped
    - Check milestone: "already new" must not be judged by storage tag alone, because the 2.0 release creates `v2.0.0+` warehouses without zstd columns that may collect leaked index copies
    - Advisory estimates: DuckDB 2.0 L2 (lock, shadow test, re-measurement, one doc page), format L2, NumPy inserts L2, HNSW rebuild L3, doctor report L2, verified copy L3, verify-only check L3, session-start hooks L2, swap kept off L3
* Insights
    - The bump changes the new-file format on its own, because 2.0's default is already `v2.0.0+`. The format milestone's explicit setting guards against a later default that lags the newest format
    - A release's head start over the next one helps only the machines that install it. Skip-safety has to live in each release, not in the release order

## 2026-10-21 - PREFLIGHT (SEVENTH RUN) - COMPLETE

* Work completed
    - Validated the 9-milestone list (DuckDB 2.0 first, skipped releases) against `projectbrief.md`, the diff from `9392fce`, the engine code, and four short DuckDB 1.5.4 and 2.0.0 experiments
    - Recorded preflight status: FAIL (fixable). The milestone list was not changed
* Decisions made
    - Prerequisites, checklist shape, scope, order, invariants, and the Done and Risks blocks pass. The checklist is a valid serial walk of the new graph
    - Fixable: brief acceptance 4 still says a new warehouse is `v1.5.0+`, against the amended use case and milestone 2's Done line
    - Fixable: the skipped-release arrivals leave out an empty `v1.0.0+` file at schema 0 (left by a failed first open). On 2.0, milestone 2's zstd clauses in `0001` raise a binder error on that file, so every writer open would fail. That breaks acceptance 11
    - Fixable: milestone 1's Done line has the sub-run rewrite later milestones' lines, which the milestones lifecycle rule forbids. One sentence of operator authority, or a hand-off through `/niko-plan`, resolves it
    - Advisory, not adopted: freeze the shadow test's baseline under the flock; build old-format fixtures from the v2.1.2 migration SQL; add a 1.5.4 writer step to the shadow test; cap duckdb below 2.1 so dependabot cannot leave the LTS line; keep a durable test that semantic search plans through the HNSW index; small brief wording fixes
    - Radical advisory, not adopted: create new files and the rewrite at `v1.5.0` storage, which 1.5.4 can open, instead of `v2.0.0`
* Insights
    - Measured: DuckDB 2.0.0 raises `BinderException` for `USING COMPRESSION zstd` on a `v1.0.0+` file. 1.5.4 stored the column uncompressed with no error. 2.0 accepts the clause at `v1.5.0` and `v2.0.0`
    - Measured: 1.5.4 and 2.0.0 can take turns reading and writing one `v1.0.0+` file with an HNSW index, and the tag stays `v1.0.0+`. 1.5.4 replays a wal that a killed 2.0 writer left (synthetic data)
    - Measured: 1.5.4 opens a `v1.5.0+` file that 2.0 created, with zstd and HNSW. It refuses a `v2.0.0+` file ("version number 999")

## 2026-10-21 - PLAN (RE-PLAN AFTER SEVENTH PREFLIGHT) - COMPLETE

* Work completed
    - Folded the three fixable findings and the advisories into `milestones.md` and `projectbrief.md`. Still nine milestones, same order and graph
    - Confirmed the binder finding (`.scratch/scripts/zstd_clause_by_storage.py`): on 2.0.0 the zstd clause raises `BinderException` at storage `v1.0.0` and gives ZSTD at `v1.2.0`, `v1.5.0`, and `v2.0.0`; on 1.5.4 it is silently uncompressed at `v1.0.0`
    - Measured (`.scratch/scripts/crashed_wal_*`): 1.5.4 opens a `v1.0.0+` file that a killed 2.0.0 writer left with a wal, plain or HNSW-indexed, read-only and read-write, and replays every row
    - Found that this machine's live shim runs this checkout (03:30 nightly cron through it), and that a Claude Code stockroom 0.16.0 (DuckDB 1.5.4) is installed beside it
* Decisions made
    - Operator: no 2.0-only release. Milestones land in order on the branch; milestones 1 to 8 ship in one release (the swap may join, off). No release carries the 2.0 lock without the new-file format and the HNSW rebuild. The operator runs the shadow test from a branch clone on his Macs before that release
    - Operator: new files and the copy use storage `v2.0.0`, not the preflight's `v1.5.0` advisory
    - Operator: this checkout's environment stays on 1.5.4 until the shadow test passes on this machine; then the branch goes live here
    - Operator: the DuckDB 2.0 sub-run may rewrite DuckDB-behaviour sentences in later milestones' Done and Risks lines (finding 3). Scope, order, and ownership changes still stop for the operator
    - Finding 1: brief acceptance 4 now says `v2.0.0+`
    - Finding 2: arrivals now include a schema-0 `v1.0.0+` file; the format milestone must open and migrate it without deleting it, despite 2.0 rejecting the zstd clause at `v1.0.0`. Old-format test fixtures use storage `v1.0.0` with the v2.1.2 migration SQL
    - Adopted advisories: frozen shadow baseline under the flock, a 1.5.4 writer step, duckdb range below 2.1, a lasting HNSW-plan test, brief wording (first release, conversion method)
    - "Already new" simplified to newest tag plus zstd on both columns, because the single release removes the released `v2.0.0+`-without-zstd state; brief requirement 10 no longer mentions leaked copies
* Insights
    - Grouping 2.0 with the format and HNSW work removed an arrival state instead of adding code to handle it
    - A dev checkout that is also the live engine turns every lock change into a production change on that machine; the commit hook's exact sync makes it immediate

## 2026-10-21 - PREFLIGHT (EIGHTH RUN) - COMPLETE

* Work completed
    - Validated the re-planned 9-milestone list against `projectbrief.md`, the diff `f3a7c31..37cf1c0`, the engine code, and new DuckDB 1.5.4 and 2.0.0 experiments
    - Recorded preflight status: FAIL (fixable). The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass, and the seventh run's three fixable findings are resolved
    - Fixable: on DuckDB 2.0.0 (vss `3685131eac`), a writer killed after inserting into the indexed `embeddings` table leaves a wal that breaks the index after replay. Semantic search fails, ingest's embedding deletes fail, and the next insert hangs while it holds the writer flock. It does not matter whether 1.5.4 or 2.0 wrote the wal. The plan needs this arrival in the list, a milestone 1 re-measure step, an owner for the heal (milestone 4 is the natural one), and protection for this machine between milestones 1 and 4
    - Advisory, not adopted: name every Make target that syncs this checkout; hold Dependabot on `main` off duckdb 2.0 until the branch merges; say which machines run the shadow test; small wording fixes
    - Radical advisory, not adopted: the writer chokepoint rebuilds the index whenever a wal existed at open or the index is missing
* Insights
    - Measured: on 2.0.0, `DROP INDEX`, then `CREATE INDEX`, then `CHECKPOINT` heals the broken state. A wal that holds only deletes or drop-then-insert replays cleanly. 1.5.4 replays every such wal with no problem
    - Measured: a 2.0.0 writer with `storage_compatibility_version` set to `'latest'` or `'v2.0.0'` keeps an existing `v1.0.0+` file at `v1.0.0+` with FSST text, and 1.5.4 still reads and writes it, including after a killed 2.0 writer

## 2026-10-21 - PLAN (RE-PLAN AFTER EIGHTH PREFLIGHT) - COMPLETE

* Work completed
    - Reproduced the eighth preflight's finding with a standalone script (`.scratch/scripts/wal_replay_hnsw_*`, scratchpad `upstream/`): on DuckDB 2.0.0, replaying a `.wal` that holds inserts into an HNSW-indexed table, written by a killed 1.5.4 or 2.0.0 writer, leaves the index broken. Query, delete, and insert raise `InternalException` on small tables; on a 384-wide, 4,000-row table the first top-k query hung (stopped at 150 s). Every checkpoint then fails fatally, so the `.wal` stays. 1.5.4 replays the same log fine. `DROP INDEX`, `CREATE INDEX`, `CHECKPOINT` repairs it. Logs holding only deletes, or inserts after `DROP INDEX`, replay fine. Loading vss before `ATTACH` (duckdb-vss #65's workaround) does not help
    - Drafted an upstream duckdb-vss issue for the operator to file (scratchpad `upstream/issue-draft.md`); no existing issue matches
    - Amended `milestones.md` and `projectbrief.md`. Still nine milestones; the doctor milestone gained the fix group and the edge `hnsw --> doctor`
* Decisions made
    - Operator: no automatic repair code. Doctor detects a leftover `.wal` (with the writer flock free) and names the fix; a troubleshooting page documents symptoms and fix
    - Operator: discoverable doctor commands never write. Every doctor write sits behind `stockroom doctor fix <name>`; the first fix is `stockroom doctor fix hnsw-wal` (drop, recreate from the HNSW milestone's definition, checkpoint, under the writer flock). The doctor milestone owns the fix group and the page
    - Operator: the work machine does not run the shadow test; the Macs and this machine do
    - Operator: draft the upstream issue; the operator files it
    - Arrivals now include a `v1.0.0+` file with a `.wal` from a killed 1.5.4 embed. The HNSW milestone states the rule that no stockroom path inserts into `embeddings` while the index exists
    - Milestone 1: shadow test adds a killed-2.0-writer step (repeated on the newest 2.0 patch at build time); the 2.0 lock is the last change into this checkout (commit hook and every `make` target sync the environment); `.github/dependabot.yaml` ignores duckdb beyond 2.0; this machine's exposure between milestones 1 and 5 is accepted with a known lossless recovery
    - Not adopted: the preflight's radical idea of a repair rule inside `warehouse.open`. Acceptance 2 needs no exception, because no automatic rebuild exists
    - Advisory estimates: DuckDB 2.0 L2, format L2, NumPy inserts L2, HNSW rebuild L3, doctor report and fix L3 (was L2: a writing subcommand group and hang-safe detection), verified copy L3, verify-only check L3, session-start hooks L2, swap kept off L3
* Insights
    - The replay bug turns a crash during embedding inserts into a stuck nightly, but the HNSW milestone's drop-before-insert design already avoids writing the log that triggers it. What remains is an arrival edge case, which the operator chose to handle with a named fix instead of automatic code

## 2026-10-21 - PREFLIGHT (NINTH RUN) - COMPLETE

* Work completed
    - Validated the re-planned 9-milestone list against `projectbrief.md`, the diff `37cf1c0..1d8ff00`, the engine code, and new DuckDB 1.5.4 and 2.0.0 experiments on stockroom's real `embeddings` shape
    - Recorded preflight status: FAIL (fixable). The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. The eighth run's finding and advisories are resolved as the operator chose. The new edge `hnsw --> doctor` agrees with the unchanged checklist
    - Fixable: the plan's replay-bug description is wrong. On 2.0.0, a writer that does not touch `embeddings` exits 0 and the `.wal` grows. Once the `.wal` passes `checkpoint_threshold` (16 MiB by default), an automatic checkpoint deletes it and keeps an HNSW index that lacks every replayed row (3,000 of 3,500), with no error. Doctor's `.wal`-only detection, acceptance 12, the page's symptoms, milestone 1's recovery note, and the premise of "no automatic repair" all need revisiting. Options: correct the paragraph, add an index-coverage fact to doctor (`pragma_hnsw_index_info()` `count` against `count(*)`), cover the fold in milestone 1, and decide milestone 4's drop-before-sweep order
    - Advisory, not adopted: doctor's flock test must not create `.warehouse.lock`; the reproduction test must not go red when a 2.0 patch fixes the bug; acceptance 11 needs a qualifier for the `.wal` arrival; bound the shadow test's killed-writer probes with a time limit; record the work machine's exposure and rollback in milestone 1
    - Radical advisory, not adopted: move `embeddings` and its HNSW index into a separate small vectors file that is rebuilt and swapped as a whole
* Insights
    - Measured: an explicit `CHECKPOINT` fails fatally on the broken state, but the automatic checkpoint at commit succeeds and folds the log into a partial index. The loud state can turn silent on its own
    - Measured: on 2.0.0, `pragma_hnsw_index_info()` `count` equals the row count on a healthy index, including after deletes, so comparing the two is a cheap read-only coverage check
    - Measured: while the broken `.wal` is present, even a `DELETE` from `embeddings` that matches no rows raises the `InternalException`, so the order of embed's orphan sweep and the index drop decides whether the next writing embed repairs the warehouse

## 2026-10-21 - PLAN (RE-PLAN AFTER NINTH PREFLIGHT) - COMPLETE

* Work completed
    - Folded the ninth preflight's fixable finding into `milestones.md` and `projectbrief.md`. Still nine milestones, same order and graph
    - Corrected the replay-bug description: a writer that does not touch `embeddings` can auto-checkpoint the `.wal` away and leave an index that silently lacks rows. Explicit `CHECKPOINT` fails only while the `.wal` remains
    - Renamed the fix to `stockroom doctor fix hnsw-rebuild`. Doctor compares `pragma_hnsw_index_info` count with `count(*)` when no `.wal` is present, and treats a missing index the same way. The troubleshooting page lists both states
    - Milestone 1's killed-writer step now crosses `checkpoint_threshold` and compares the index count with the row count. The exposure window ends at the HNSW milestone; the fix arrives at the doctor milestone
    - The HNSW milestone drops the index only around inserts. Embed's orphan delete, which runs after the insert transaction on every embed, and ingest's delete for a removed or text-changed message, leave the index in place
* Decisions made
    - Operator: no automatic repair. About five installs, embed nightly, rollout of a couple of days. Build for a finished embed. A power loss may require the troubleshooting page. It must not empty the warehouse or delete its rows
    - Operator, from the prior session: doctor-only plus a coverage check. Confirmed here, with the command name `hnsw-rebuild`
    - Not adopted: the ninth preflight's advisories, including doctor opening `.warehouse.lock` without creating it, a reproduction test that skips if a patch fixes the bug, a timed child around the shadow-test probes, and naming the work machine's rollback in milestone 1. Acceptance 11 now points at acceptance 12 for a warehouse left mid-embed, because that is the operator's power-loss rule
    - Not adopted: the radical idea of moving `embeddings` and its HNSW index into a separate file
* Insights
    - A later embed that inserts recreates the index from every row, so that recreate includes rows a partial index had lacked. An idle night does not rebuild
    - Today's embed runs the orphan delete after the insert transaction, not before it

## 2026-10-21 - PREFLIGHT (TENTH RUN) - COMPLETE

* Work completed
    - Validated the re-planned 9-milestone list against `projectbrief.md`, the engine code, and new DuckDB 1.5.4 and 2.0.0 experiments on delete-and-checkpoint growth
    - Recorded preflight status: FAIL (fixable). The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass as structure. The ninth run's fold, coverage check, and `hnsw-rebuild` fix are in the plan
    - Fixable: a delete of `embeddings` rows with the HNSW index left in place leaks a full index copy. On 1.5.4, one single-row delete plus checkpoint grew a 1,500-row file by exactly the index (10 blocks of 262144). Two further deletes kept adding copies. Process close does it with no explicit checkpoint, on 1.5.4 (wal of 125 bytes) and on 2.0.0 (wal of 159 bytes). A delete that matches nothing does not. Ingest closes its connection after `write_session` deletes embeddings, and embed skips the drop when it inserts nothing, so removal nights keep the copy
* Insights
    - The 2.0 move does not remove this leak. A later drop returns the copies to the free list on a small file; issue 147 already measured that the real warehouse does not shrink
    - Advisory, not adopted: `hnsw-rebuild` has to create the index when it is already missing. Radical advisory, not adopted: ingest records dirty owner ids and embed is the only process that changes `embeddings`, so a night pays one rebuild

## 2026-10-21 - PLAN (RE-PLAN AFTER TENTH PREFLIGHT) - COMPLETE

* Work completed
    - Folded the tenth preflight's fixable finding into `milestones.md` and `projectbrief.md`. Still nine milestones, same order and graph
    - A process that adds or removes `embeddings` rows drops the index before those statements, recreates it, and checkpoints before it exits. A delete that matches nothing is not a change, and a process that changes nothing does not rebuild
    - Ingest does this around its delete for a removed or text-changed message, before it closes the connection. Embed drops once around its inserts and an orphan delete that removes rows
    - The growth test includes a process that deletes rows and exits without inserting
    - `stockroom doctor fix hnsw-rebuild` creates the index when it is already missing, and drops it only when one exists
* Decisions made
    - The operator's "deletes leave the index in place" line is amended by the measurement. Keeping it would let removal nights grow the file by an index copy, which fails acceptance 1. The power-loss rule is unchanged: a crash must not empty the warehouse
    - Adopted the advisory that the fix command has to succeed when the index is already gone, because the probe already names that command for a missing index
    - Not adopted: making embed the only process that changes `embeddings`. A night that both invalidates and inserts pays two index builds. That is the smaller fix the preflight named
* Insights
    - The leak is at checkpoint and at process close, on 1.5.4 and 2.0.0. Ingest's close after `write_session` is the certain one, because ingest and embed are separate processes

## 2026-10-21 - PREFLIGHT (ELEVENTH RUN) - COMPLETE

* Work completed
    - Validated the re-planned 9-milestone list against `projectbrief.md`, the engine code, and delete-and-exit cycles on DuckDB 1.5.4 and 2.0.0
    - Recorded preflight status: PASS WITH ADVISORY. The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. The tenth run's delete-leak finding is in the plan, and the planned drop, delete, recreate, checkpoint cycle keeps used blocks flat on both DuckDB versions
    - Advisory, not adopted: checkpoint while the index is down, before `CREATE INDEX`, and bound the growth test on used blocks. The single trailing checkpoint alternates the file by one index
    - Advisory, not adopted: ingest keeps the index down across every `write_session` in the process. Recreating between two embedding deletes leaves one used index copy
    - Radical advisory, not adopted: one helper is the only embeddings mutator, and it checkpoints the dropped index before it builds the new one
* Insights
    - On a 1,500-row fixture the control delete climbs every cycle. The planned cycle stays at 20 used blocks. `DROP INDEX` then `CHECKPOINT` before the delete stays within one block of the start on every cycle, on 1.5.4 and 2.0.0, with the same numbers on both

## 2026-10-21 - REVIEW (ADVISORY 1) - COMPLETE

* Work completed
    - Wrote the operator's decision into the HNSW milestone and acceptance 1. The milestone list is unchanged
* Decisions made
    - The growth test asserts, on every cycle, used blocks or a high-water file size of one index over the start. A cycle's file may be larger than the previous cycle by that one free index
    - Not adopted: checkpoint while the index is down. That pass only removes free blocks the next cycle reclaims. The plan checkpoints once, after the recreate
* Insights
    - The leak is used blocks that stay up. The breath is file size. The test has to be able to tell them apart

## 2026-10-21 - REVIEW (ADVISORY 2) - COMPLETE

* Work completed
    - Wrote the write order into the HNSW milestone, the happy path, and acceptance 1. The milestone list is unchanged
* Decisions made
    - The index stays down until every embedding delete in the process has run. The process recreates once, after the last one. The growth test includes two deletes and one recreate, with the recreate after both
    - A message rewrite that does not change embeddings does not keep the index down
    - Not adopted: a single helper as the only code allowed to change `embeddings`. The order is the requirement
* Insights
    - This is the same leak as an index-up delete. DuckDB 2.0 and the new file format do not remove it. Asking the operator to choose the order was a mislabel: the preflight called a misreadable sentence an advisory

## 2026-10-21 - MILESTONE 1 SUB-RUN (DUCKDB 2.0) - BUILD FAIL, SUPERSEDED BY RE-PLAN

* Work completed
    - Level 3 sub-run for "Move the engine to DuckDB 2.0 and prove it on a copy of a real warehouse": plan, eight preflights, and build. Its full record is in git at `bd910c3` (`memory-bank/active/progress.md` and `tasks.md`)
    - Built and committed on this branch: the schema-1 storage-tag test, the unscoped-HNSW plan test, `scripts/shadow_duckdb_20.py` with 14 tests, version-free wording for the scoped-filter reason, and a 4,096-row scoped starvation fixture
    - The synthetic section passed on DuckDB 2.0.0. The live run on a copy of this machine's warehouse passed through branch A, then failed at branch B: `expected folded, got healthy`
* Decisions made
    - The 2.0 lock never landed. This checkout stays on DuckDB 1.5.4, and the live warehouse was only flocked, checked, copied, and stat'ed
    - Operator: drop the HNSW index, a two-way door; strip everything about the index except the migration that drops it; re-plan the L4 milestones
* Insights
    - The live index reads 280,901 entries for 133,793 rows while healthy, on 1.5.4 and 2.0.0. `hnsw_compact_index` leaves the count; a rebuild (21 s) makes it equal and restores full top-100 results. So a fold cannot be detected from counts on a real warehouse
    - Exact top-100 search over the same rows: 130 ms median on 2.0.0, 164 ms on 1.5.4, always 100 rows. Through the index: 34 ms and 41 ms, 37 to 65 rows
    - `DROP INDEX` and a checkpoint on the live copy: 0.8 s, used blocks 161,453 to 6,846, 37.4 GiB freed inside the file. `COPY FROM DATABASE` of the result: 506 MB in 5.2 s
    - DuckDB 2.0.0 filters a scoped `WHERE` inside the HNSW scan; DuckDB 2.0.0 rejects the SQL lambda arrow `x -> ...`; under 2.0.0, `stockroom embed` and `stockroom semantic` print nanobind leaked-instance warnings at exit (cause unknown)

## 2026-10-21 - PLAN (L4 RE-PLAN: DROP THE HNSW INDEX) - COMPLETE

* Work completed
    - Rewrote `milestones.md`: eight milestones. Dropping the index and `vss` comes first, then DuckDB 2.0, then the new file format and the doctor storage report, then the verified copy, the verify-only check, its session-start launch, and the swap kept off
    - Rewrote `projectbrief.md` for the decision: requirements, use cases, constraints, and acceptance no longer keep the index, the NumPy insert path, or a doctor fix
* Decisions made
    - Drop the HNSW index and `vss`: estimated L3. A migration, the warehouse chokepoint, semantic search, schema snapshots, tests, docs, and the shadow script all change, and the first commit with the migration goes live on this machine
    - DuckDB 2.0: estimated L3. The pin, Dependabot, the shadow script without its kill branches, a live-copy run before the lock lands, and the nanobind warnings
    - New file format and ZSTD: estimated L2. One creation path, two column clauses, the schema-0 case, and one doc page
    - Doctor storage report: estimated L2. Read-only facts on the existing probe, with no index lines and no fix
    - Verified copy: estimated L3. Equality, catalog, zstd on the copy, and the old-format fixture, with the original untouched
    - Verify-only check: estimated L3. Flock, skip rules, the record, the time limit, cleanup, and faults
    - Session-start launch: estimated L2. Two hook files and a detached launch
    - Swap kept off: estimated L3. Hard link, replace, fsync, the SHA-256 proof, and faults after the link and the replace
    - Cut from the plan: the HNSW drop-and-recreate milestone, the NumPy insert milestone, doctor's `.wal` and index-coverage lines, `stockroom doctor fix hnsw-rebuild`, the replay-bug troubleshooting page, and the HNSW checks in the copy
    - `vss` leaves the engine, not only the index. Measured on 1.5.4 and 2.0.0 with autoload off: a file with the index, with or without a leftover `.wal` from a killed 1.5.4 embed, opens without `vss`, keeps every row, runs an exact cosine query, and drops the index inside a transaction
    - Releases: milestones 1 and 2 make the first release, and milestone 1 may ship alone before it. This replaces "milestones 1 to 8 ship together", whose reason was the HNSW rebuild
    - DuckDB facts in the later milestones are the ones measured on 2.0.0 on 2026-10-21, so the 2.0 milestone no longer re-measures and rewrites them
* Insights
    - With the index gone, copying this machine's warehouse takes seconds and about 0.5 GB. The verify-only release before the swap was sized for a long rebuild of a 39 to 88 GB file. The plan keeps it, because it is the operator's decision and not about the index; the operator can fold it into the swap at review

## 2026-10-21 - PREFLIGHT (TWELFTH RUN) - COMPLETE

* Work completed
    - Validated the 8-milestone "drop the HNSW index" list against `projectbrief.md`, the engine code, and new DuckDB 1.5.4 and 2.0.0 experiments, including read-only runs on the scratchpad copy of this machine's warehouse (no write; size and mtime unchanged)
    - Recorded preflight status: PASS WITH ADVISORY. The milestone list was not changed
* Decisions made
    - All seven Level 4 checks pass. Every requirement, proof, and acceptance item maps to a milestone. The checklist is a valid serial walk of the graph, and each shared artifact has a handoff rule
    - Advisory, not adopted: milestone 1's single exact path removes duplicate chunks (max-sim) and cuts to the limit before it joins `messages.text`. Run with no scope, today's scoped SQL takes 1.3 s on 2.0.0 and 1.7 s on 1.5.4 on this machine's data. The dedup-first shape takes 153 ms and 205 ms
    - Advisory, not adopted: milestone 1's leftover-wal test opens through `warehouse.open()` in a DuckDB instance that never loaded vss, and asserts vss is not loaded. Connections to the same path in one process share the database and the extensions loaded in it
    - Advisory, not adopted: the zstd checks in milestones 3 and 6 look only at data segments (VARCHAR or JSON) and say what an empty table means. VALIDITY segments show `Uncompressed` or `Constant` under zstd
    - Radical advisory, not adopted: merge the swap into the check as a per-machine two-phase record (rehearsed, then swapped at a later session start), dropping the separate enable release
* Insights
    - With the engine's default config (autoload and autoinstall on), DuckDB 1.5.4 and 2.0.0 never load vss by themselves for a file with the index, read-only or read-write, with or without a killed embed's wal
    - The live data's tables copy to 288 MiB with zstd, against 483 MiB without, in about 6 s on 2.0.0
    - On 2.0.0 without vss, `COPY FROM DATABASE` fails on a file that still has the index. A comment-only migration file runs on both versions

## 2026-10-22 - REVIEW (OPERATOR) - COMPLETE

* Work completed
    - Folded the twelfth preflight's three advisories into `milestones.md`: the dedup-first search shape and the separate-process leftover-`.wal` test in milestone 1, and a zstd data-segment invariant used by milestones 3, 5, and 6
    - Merged the swap milestone into the check milestone, leaving 7 milestones. Updated the invariants, shared artifacts, execution order, the hook milestone, and `projectbrief.md` (spec note, lifetime, existing-warehouse use case, requirements 2, 3, and 6, and acceptance 4 and 7)
* Decisions made
    - Operator: adopt advisories 1 to 3
    - Operator: merge the swap into the check (the radical advisory). Phase A records `rehearsed`. Phase B runs at a later session start, at least one day after a `rehearsed` record of the same check version: it copies again, verifies, hard-links the original to the backup name, and replaces the live file. This reverses "the check's first release never swaps". The kill switch is a release that changes the check version and keeps phase B off
    - A filesystem that refuses hard links is now a skip reason, tested before the pass builds
    - The merged list was not preflighted again; the operator directed it at review
* Insights
    - Without the index, the rehearsal measures a copy of 288 MiB built in under 6 s, so a release spent collecting field data before any swap no longer buys much
