# Progress

`stockroom doctor` probe prints file size, used blocks, free blocks, a reclaimable estimate, the storage format, free disk, and, when a backup file is present, its path and size. The report does not write. When the warehouse is missing, behind the schema head, or busy, the report still prints the facts that need no database connection.

**Complexity:** Level 2

## 2026-10-23 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed tag `v3.0.0` is commit `c9fbcc4` on `main`
    - Restored `memory-bank/active` onto `warehouse-file-growth` from `constrain-size-as-best-we-can`
    - Checked milestone 3 after its reflect phase
    - Classified milestone 4 as Level 2
* Decisions made
    - Level 2. The change is one read-only section on the existing doctor probe. The L4 milestone already fixes the facts, the reclaimable estimate, and the no-write rule
* Insights
    - Apart from version files, `v3.0.0` and `constrain-size-as-best-we-can` differ in `memory-bank/active` and SumMem notes

## 2026-10-23 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 2 plan for the doctor storage report
    - Named the swap backup `warehouse.issue147-swap.duckdb`
    - Left the check-record line on milestone 6
* Decisions made
    - Doctor reads with `resolve_home` and a read-only connect. Doctor does not call `home_dir` or `open_current`
    - The reclaimable estimate is file size minus distinct persistent block ids times `block_size`
    - A busy lock or a failed read prints the stat facts and does not raise
* Insights
    - `pragma_database_size` on DuckDB 2.0 exposes `used_blocks`, `free_blocks`, and `block_size`
    - `open_current` creates the home through `home_dir` and refuses a behind-head file, so doctor cannot use `open_current`
