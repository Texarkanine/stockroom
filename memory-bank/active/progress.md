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

## 2026-10-23 - PREFLIGHT - COMPLETE

* Work completed
    - Ran Level 3 preflight on the verified newer-format copy
    - First line of `.preflight-status` is `FAIL (fixable)`
* Decisions made
    - The plan changes before build: catalog reads after `ATTACH` must filter to the current database, and constraint equality must ignore `constraint_index` while the other file is attached
* Insights
    - On DuckDB 2.0.0, `duckdb_tables()` after `ATTACH` lists every base table twice, and the second `INSERT BY NAME` hits the primary key
    - `constraint_index` shifts once the other file is attached; the same helper matches in full when each file is opened alone
    - The specified two-row fixture stores `messages.text` as `(VARCHAR, ZSTD)` and `tool_calls.tool_input` as `(JSON, ZSTD)`

## 2026-10-23 - PLAN - COMPLETE

* Work completed
    - Revised the copy plan for the fixable preflight finding
* Decisions made
    - `DELETE`, `INSERT`, and `EXCEPT ALL` take base-table names from `database_name = current_database()`
    - `_introspect_schema`, `_constraints`, and `_tables_sql` run on two connections that have attached nothing. The full constraint rows, including `constraint_index`, are the compare
    - The advisory `read_catalog` helper is not added. Table SQL stays in the compare, with the zstd clause removed
* Insights
    - Preflight copied the two-generation fixture on DuckDB 2.0.0. Both `EXCEPT ALL` directions were empty once the table list was filtered, and the copy's version-9 filename was `0009_drop_vector_index.sql`
