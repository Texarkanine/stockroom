# Progress

Milestone 1 of L4 project `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147)): a brand-new warehouse file is created in DuckDB's newer storage format (tag `v1.5.0+`), and `messages.text` and `tool_calls.tool_input` are created `USING COMPRESSION zstd`, shown by `pragma_storage_info` after a write. Existing populated files are not rebuilt and stay outside `schema_version`. `docs/advanced/duckdb.md` says a new file uses the current format and that DuckDB 1.4.5 cannot read it. See `memory-bank/active/milestones.md` (milestone 1) and `memory-bank/active/projectbrief.md`.

**Complexity:** Level 2

## 2026-10-21 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - `/niko` re-entry: L4 plan final (sixth preflight PASS WITH ADVISORY, post-preflight fixes folded in), no sub-run classified yet
    - Milestone 1 classified as Level 2
    - Fresh sub-run state written: `progress.md`, `activeContext.md`, stubbed `tasks.md`. `projectbrief.md` and `milestones.md` preserved
* Decisions made
    - Level 2, matching the milestone's estimate: a self-contained enhancement to one creation path, two column clauses in `0001`, and one doc page
* Insights
    - The L4 preflights measured on DuckDB 1.5.4: `USING COMPRESSION zstd` survives migration `0004`'s `ALTER TABLE ... ADD COLUMN` on a `v1.5.0+` file; on an old-format file the clause gives no error and stores the column uncompressed; connecting an existing file with `storage_compatibility_version = 'latest'` leaves it at `v1.0.0+`
    - Milestone 5 relies on this milestone's `0001` definition when it runs migrations on the empty copy, so the clauses live in `0001`, not in a new migration
