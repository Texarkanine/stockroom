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

## 2026-10-23 - PREFLIGHT - COMPLETE

* Work completed
    - Preflight of the milestone 4 doctor storage report
    - Wrote `memory-bank/active/.preflight-status`
* Decisions made
    - First line of `.preflight-status` is `FAIL (fixable)`
    - Existing probe callers that do not already isolate the home must use a temp home before build, so the suite does not open the live warehouse
* Insights
    - Same-process `LOCK_EX|LOCK_NB` blocks, and `warehouse.open` keeps `.warehouse.lock` until the connection object is finalized, not when `close()` returns
    - Persistent `block_id` `-1` is a constant-segment sentinel; per-table sums double-count a shared id; `pragma_storage_info` raises on views
    - A read-only connect does not create a missing file, and it works after a storage-config connection is closed

## 2026-10-23 - PLAN - COMPLETE

* Work completed
    - Revised the plan for the fixable preflight finding and the four advisories
* Decisions made
    - Existing probe callers that do not already isolate the home set `STOCKROOM_HOME` to an empty temp home. `_probe` does not set that variable
    - `live_bytes` unions persistent block ids across base tables, drops ids below 0, and skips views
    - A missing warehouse file is `warehouse: absent`. Probe does not connect
    - The happy-path test drops the writer connection and collects garbage before probe
* Insights
    - `block_id` `-1` is a constant-segment sentinel and is not a file block

## 2026-10-23 - PREFLIGHT - COMPLETE

* Work completed
    - Re-ran preflight on the revised milestone 4 doctor storage report
    - Wrote `memory-bank/active/.preflight-status`
* Decisions made
    - First line of `.preflight-status` is `PASS WITH ADVISORY`
    - The plan is acceptable as written. The overhead constant and the wider help sentence stay advisory
* Insights
    - On an empty `build_warehouse` file, `free_blocks` is 0 and file size minus the column-block union is 536576 of 798720
    - A cross-process read-only connect fails immediately when a writer holds the DuckDB lock

## 2026-10-23 - BUILD - COMPLETE

* Work completed
    - Doctor probe reports warehouse size, block use, reclaimable space, storage format, free disk, and the swap backup without writing
    - Help text and the contributor probe comment name those facts
    - `make ci` passed: 1098 pytest passed, 39 skipped; 134 JavaScript tests passed
* Decisions made
    - `live_bytes` stays the persistent block-id union. The overhead advisory was not adopted
    - `--help` uses `RawDescriptionHelpFormatter` so the storage phrases stay intact
* Insights
    - argparse wraps the description and can split a two-word phrase such as `free disk` across lines
