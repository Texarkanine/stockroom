# Progress

Extend the milestone 3 warehouse builder so it can copy an existing warehouse into a verified newer-format sibling. The original stays read-only and unchanged. The copy is built from the frozen schema file, with zstd on `messages.text` and `tool_calls.tool_input`, then checked for multiset equality in both directions and catalog equality. The builder returns sizes and times. This milestone does not replace the live file and does not start the check.

**Complexity:** Level 3

## 2026-10-23 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Checked milestone 4 after its reflect phase
    - Removed the milestone 4 sub-run files
    - Classified milestone 5, the verified newer-format copy, as Level 3
* Decisions made
    - Level 3. The change is a complete copy-and-verify feature on the existing builder. The L4 milestone already fixes the design, so this sub-run does not reopen architecture
* Insights
    - Milestone 6 is the one the L4 plan says to split if classification comes out above Level 3. Milestone 5 has no such split

## 2026-10-23 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan for the verified newer-format copy
    - Probed `ATTACH`, `INSERT BY NAME`, a plain reconnect, and one-row zstd on temp files in this checkout
* Decisions made
    - The sibling is `warehouse.copy.duckdb` beside the original. Success leaves it. Milestone 6 deletes it or swaps it
    - `apply_pending` and `build_warehouse` gain keyword-only `through`. The copy passes the original's schema version
    - Catalog equality strips the zstd clause and compares view columns. It does not compare view SQL text
    - No docs edit. Nothing a user can run calls the copy yet
* Insights
    - One long `VARCHAR` row and one small `JSON` row store as persistent `ZSTD` when the table was created with the clause
    - A `v1.0.0` file and a `v2.0.0` file reload the same view with different parentheses, so view SQL is the wrong equality check
