# Progress

L4 milestone 3 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): restore every released migration as it shipped, and create new warehouses from a frozen schema file in DuckDB 2.0's storage format with zstd on `messages.text` and `tool_calls.tool_input`. `0001` to `0008` get their released SQL back (comments may differ), `0003_embeddings_hnsw_index.sql` returns under its own name, and a `make ci` and CI gate fails when a released migration's SQL differs from the latest release tag. A frozen version-9 schema file outside the migrations folder creates new warehouses at an explicit `v2.0.0` storage version, under a temp name renamed into place under the writer flock, with one `schema_version` row naming it, then migrates them forward. A test keeps it equal to the chain at version 9, apart from compression. A warehouse at schema 3 to 8 migrates to the head without `vss`; one below schema 3 stops with an error that names the file and says to move it aside. Old-file builders load `vss` only in a separate process. Docs and `memory-bank` describe the schema file and the immutability rule. The new-warehouse path runs once on this machine's real transcripts in a scratch home. Milestones 1 to 3 make the first release.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Cleared the L4 preflight status file (its findings are folded into `milestones.md` and `projectbrief.md`)
    - Classified milestone 3, "Restore every released migration as it shipped and create new warehouses from a frozen schema file in DuckDB 2.0's storage format with ZSTD on messages.text and tool_calls.tool_input"
* Decisions made
    - Level 3, as the L4 re-plan estimated. Most of the restoration copies files back from `main`. The new code is the schema file and its equality test, the create path with temp-then-rename, the stop rule, and the immutability gate. All of it sits in the warehouse creation and migration subsystem

## 2026-10-22 - PLAN - COMPLETE

* Work completed
    - Wrote the Level 3 plan in `tasks.md`: 9 steps and 35 behaviours (G1 to G8 for the immutability gate, S1 to S10 for the schema file and builder, W1 to W8 for `open()` and the CLI, R1 to R7 for the restored chain, H1 and H2 for the shadow script)
    - Probed DuckDB 2.0.0 in the scratchpad (`m3/probe_released_chain.py`, `probe_unbound_checkpoint.py`, `probe_unbound_close.py`, `probe_rw_open_bytes.py`, `probe_gate_tokens.py`)
* Decisions made
    - The released chain for tests is built in a child process that loads `vss`; the pytest process reads those files without it
    - The floor stop (below schema 3) is in the warehouse chokepoint, with a new typed error; `apply_pending` is unchanged
    - A new warehouse is linked into place (`os.link`, then `os.unlink` of the temp name), so creation can never replace an existing file
    - The gate compares SQL tokens against the highest `v*` tag and also covers `schemas/`, because a schema file is frozen like a migration
    - Order: gate, schema-file path, create and stop, `migrated_con`, then the restoration (preflight advisory 8), so no commit needs the released `0003` for a new install
* Insights
    - DuckDB 2.0.0 without `vss`, on a file with the HNSW index: an explicit `CHECKPOINT` after an `ALTER`, `INSERT`, or `CREATE VIEW` raises `FatalException`, but a plain close checkpoints fine. The runner's `0004` to `0009`, a kill mid-chain, and a tiny `checkpoint_threshold` all reach 9 with every row. The engine runs no explicit `CHECKPOINT`, so only test code could trip it
    - DuckDB re-prints view SQL in a form that does not round-trip, so the schema file copies `0007`'s view text word for word
    - `embed` runs in one transaction, so a time-killed embed keeps nothing; a "bounded" real-data embed needs a smaller source, not a kill
