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

## 2026-10-23 - PREFLIGHT - COMPLETE

* Work completed
    - Ran Level 3 preflight on the revised verified-copy plan
    - First line of `.preflight-status` is `PASS WITH ADVISORY`
* Decisions made
    - The revised plan is acceptable to build. Row copy and `EXCEPT ALL` use the current database only. Catalog reads, including `constraint_index`, use connections that have attached nothing
* Insights
    - The planned `through=9` tests stay green if `through` means "apply nothing". A case where version 10 is inside the ceiling would lock the predicate
    - `_introspect_schema` already matches a `v1.0.0` chain at version 9 and a `v2.0.0` schema-file warehouse through `0009_snapshot.json`, so the copy test's column compare is an existing contract
    - Milestone 6 treats verification mismatch as final. Table-text formatting inside `CopyMismatch` would make a DuckDB pretty-printer change end the check

## 2026-10-24 - BUILD - COMPLETE

* Work completed
    - `apply_pending` and `build_warehouse` stop at a keyword-only `through` version
    - `copy_warehouse` builds `warehouse.copy.duckdb` from the schema file, copies rows, verifies, and returns sizes and times
    - The two-generation fixture is built in the worker. This process does not load `vss`
    - Engine suite 1110 passed and 36 skipped with torch installed. Coverage collection 4 passed. Dashboard JS 134 passed
* Decisions made
    - A populated large column must store zstd data segments. An empty column has no data segment and does not fail verification
    - Row compare and the row copy list base tables for the current database. Catalog compare opens each file with nothing attached
* Insights
    - A short `messages.text` row in the schema-file sibling lands as persistent ZSTD. The one-row chain has no tool call, so that column is empty
    - Patching `migrations_dir` with a function that calls `discover()` recurses. Build the folder, then patch

## 2026-10-24 - QA - COMPLETE

* Work completed
    - Reviewed the verified newer-format copy against the milestone 5 plan
    - Wrote `memory-bank/active/.qa-validation-status`
* Decisions made
    - PASS. The implementation is acceptable as-is. Advisories stay advisories
* Insights
    - `through` stops at the original's version. The positive "apply up to the ceiling" case is not a test
    - Catalog equality runs on unattached connections. The fault injection covers a deleted row, not a dropped view
