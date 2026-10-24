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
