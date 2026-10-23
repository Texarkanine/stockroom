# Progress

L4 milestone 3 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): create new warehouses in the newest DuckDB storage format with zstd on `messages.text` and `tool_calls.tool_input`. A brand-new warehouse file carries the newest storage tag the pinned DuckDB writes (`v2.0.0+` on 2.0), set explicitly when the file is created. The data segments of both columns show zstd after a write. Existing populated files are not rebuilt, and a stockroom writer that opens one leaves its storage tag unchanged. A `v1.0.0+` file at schema 0 (the empty file a failed first open left behind) still opens and migrates to head without being deleted.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Checked off milestone 2 in `milestones.md` and cleared its sub-run files (its reflection stays in `reflection/`)
    - Classified milestone 3, "Create new warehouses in the newest DuckDB storage format with ZSTD on messages.text and tool_calls.tool_input"
* Decisions made
    - Level 3. The change spans the one production connect site (`warehouse.py`), migration `0001`, how the runner treats a `v1.0.0+` schema-0 file (the zstd clause raises `BinderException` there), and the test helpers in about nine test files that build old files. Two design choices are open: `'latest'` or an explicit 2.0 storage version, and how `0001` runs on an old empty file
* Insights
    - Only `warehouse.py:211` connects in production code, so the storage setting has one home. A second read-write connection in one process with another storage setting raises `ConnectionException`, so every connection must agree on it

## 2026-10-22 - PLAN - COMPLETE

* Work completed
    - Probed DuckDB 2.0.0 storage behaviour with scratch scripts (`scratchpad/m3/probe_storage.py`, `probe_followup.py`) and timed reads on zstd and plain copies of this machine's tables (`measure_zstd_reads.py`, from the milestone 2 backup attached read-only)
    - Wrote the Level 3 plan in `tasks.md`: 6 behaviours (R1 and R2 for the runner, W1 to W4 for the warehouse) and steps 0 to 6
* Decisions made
    - An explicit `warehouse.STORAGE_VERSION = "v2.0.0"` on every engine connect, read-only and read-write. `'latest'` moves with a DuckDB bump and still conflicts with plain connects. The setting leaves old files' tags alone, and 1.5.4 still reads and writes them
    - The runner drops `USING COMPRESSION zstd` when the current database's tag is older than `v1.2.0`, where DuckDB refuses it. The bare schema-0 leftover migrates in place with plain columns
    - No creative phase: both questions were settled by measurement
    - Where milestone 3's commits go is the operator's call before build (step 0)
* Insights
    - DuckDB 2.0.0 already defaults to `'latest'` (`v2.0.0+`), so W1 must change the constant to prove the engine sets it explicitly
    - A plain `v2.0.0` file stores `messages.text` uncompressed: 489 MiB plain against 290 MiB with zstd, and a full-text scan takes 142 ms against 196 ms
    - The schema-0 leftover from v2.1.2 has no tables at all: `ensure_vss` ran before `apply_pending`
