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
