# Progress

Run the verified copy under the writer flock, with a time limit, as one check pass. Phase A records a rehearsal and deletes the copy. Phase B, at least one day later, copies the warehouse again, hard-links the original to the backup name, and replaces the live file. The pass skips when the warehouse is not ready. Nothing starts the pass yet. Doctor gains one line for the check record.

**Complexity:** Level 3

## 2026-10-24 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Checked milestone 5 after its reflect phase
    - Removed the milestone 5 sub-run files
    - Classified milestone 6, the check pass, as Level 3
* Decisions made
    - Level 3. The change is one check pass on the copy milestone 5 already builds. The L4 milestone already fixes the design, including phase A, phase B, the skip list, and the time limit, so this sub-run does not reopen architecture
    - Did not split the milestone. The plan says to split into a rehearsal milestone and a swap milestone only if classification comes out above Level 3
* Insights
    - Milestone 7 is what turns the pass on. This sub-run leaves it dormant

## 2026-10-24 - CREATIVE - COMPLETE

* Work completed
    - Chose the check pass time limit
* Decisions made
    - The alarm ceiling is 4 hours (`14400` seconds). `run_check` does not set the alarm. The entry point does, with the default terminate action
* Insights
    - The ceiling is for a stuck pass. A healthy copy releases the flock when it finishes
    - Overrun is final, so a short ceiling is the outcome that needs a person

## 2026-10-24 - CREATIVE - COMPLETE

* Work completed
    - Measured a copy's peak files, then chose the free-disk comparison
* Decisions made
    - Skip when free disk is below `2 * live_bytes + 64 MiB`
* Insights
    - On a 2000-row zstd fixture the wal peaked at about 20 MB, the logical text, while live bytes stayed 524,288. That fixture is already new, so the check does not copy it
    - For a file the check does copy, live bytes include the uncompressed text, and the wal is about that size again

## 2026-10-24 - CREATIVE - COMPLETE

* Work completed
    - Chose the doctor word for a started entry whose time limit has passed
* Decisions made
    - Inside the limit the line says `running` and a later pass does not build
    - Past the limit the line says `overrun` and the entry is final. Doctor does not print `crash`
* Insights
    - The alarm cannot write a status. The clock is the only signal that separates running from overrun
    - The writer flock cannot separate them. Ingest and the nightly job hold that same flock

## 2026-10-24 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan for the check pass
    - Measured peak files during a copy of an already-zstd fixture before choosing the disk margin
* Decisions made
    - The pass lives in `stockroom.check` and is not a user-facing subcommand
    - Phase A writes `rehearsed` before it deletes `warehouse.copy.duckdb`. Phase B calls `copy_warehouse` again
    - Doctor prints one `check` line. Inside the limit it says `running`. Past the limit it says `overrun`
* Insights
    - A started entry that is still inside its limit must not have its sibling deleted. That sibling belongs to the pass holding the flock
    - `statvfs` `ST_RDONLY` is the read-only skip. A directory that is merely mode `0555` is a different failure

## 2026-10-24 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the milestone 6 check-pass plan against the engine
    - Wrote `memory-bank/active/.preflight-status`
* Decisions made
    - First line of `.preflight-status`: `FAIL (fixable)`
    - The plan was not edited. No test step was out of order, and no step was a change-detector
* Insights
    - A schema-file warehouse is already new under this plan, so the alarm test never reaches a sleeping `copy_warehouse` or a `started` record
    - A stored `skip` has no `next_action` result that builds again, and the diagram sends that case to quiet

## 2026-10-24 - PLAN - COMPLETE

* Work completed
    - Revised the check-pass plan for the fixable preflight findings
    - Took the four advisories into the plan: lazy imports, the zstd message helper, measurements on `swapped`, and a `linked` resume
* Decisions made
    - `next_action` on `skip` returns `phase-a`, and the readiness ladder still runs before a build
    - The alarm child uses `generations_file` and patches the `copy_warehouse` that child calls
    - A `v2.0.0+` file with a non-zstd segment on either large column is not `already-new`
    - After `os.link` succeeds the record is `linked` before `os.replace`. `linked` finishes the swap and does not copy again
* Insights
    - A schema-file warehouse is already new under this plan, so it cannot be the warehouse that sleeps inside `copy_warehouse`
    - A final `started` entry plus a backup left by `os.link` would make every later link fail, including after the record is deleted

## 2026-10-24 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the revised milestone 6 check-pass plan against the engine
    - Wrote `memory-bank/active/.preflight-status`
* Decisions made
    - First line of `.preflight-status`: `FAIL (fixable)`
    - The plan was not edited. No test step was out of order, and no step was a change-detector
* Insights
    - Cleanup deletes `warehouse.copy.duckdb` before `finish-swap`, and that sibling is the verified copy the resume has to rename into place
    - The backup inode, the warehouse inode, and the sibling name are enough to finish a replace that died before the record reached `linked`

## 2026-10-24 - PLAN - COMPLETE

* Work completed
    - Revised the check-pass plan for the second fixable preflight
    - Took the fixture, allow-list, free-byte, and spy advisories into the plan
* Decisions made
    - A `linked` record finishes before leftover cleanup. Matching inodes and a sibling means replace that sibling and write `swapped` from the stored measurements. Differing inodes means write `swapped` and then delete a stray sibling. A missing sibling leaves the record `linked`
    - Finish-swap does not run the readiness ladder
    - An expired `started` entry stays final and does not replace, even when the backup inode matches the warehouse
* Insights
    - The directory-entry resume would close the gap before `linked` is durable. It would also replace a warehouse the creative decision keeps final, so it stays out of this plan

## 2026-10-24 - PREFLIGHT - COMPLETE

* Work completed
    - Validated the third milestone 6 check-pass plan against the engine
    - Wrote `memory-bank/active/.preflight-status`
* Decisions made
    - First line of `.preflight-status`: `PASS WITH ADVISORY`
    - The plan was not edited. No test step was out of order, and no step was a change-detector
* Insights
    - A messages row that omits `text` still gets a persistent `DICT_FSST` segment once the zstd clause is removed, so that fixture is not already new
    - Publishing the backup under a partial name until `linked` is durable would keep a crash in that window from blocking every later `os.link`

## 2026-10-24 - OPERATOR

* Decisions made
    - The gap between `os.link` and a durable `linked` record is accepted. Do not code against it for this change
    - Hard link stays. It keeps the old inode without a second copy of the old file
    - File size stays out of the swap decision
* Insights
    - The rebuild is the long part. The link, the record write, and the rename are once per machine after that rebuild
