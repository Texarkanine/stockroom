# Progress

L4 milestone 3 of 7 for `warehouse-file-growth` ([issue 147](https://github.com/Texarkanine/stockroom/issues/147), as amended in `memory-bank/active/projectbrief.md`): restore every released migration as it shipped, and create new warehouses from a frozen schema file in DuckDB 2.0's storage format with zstd on `messages.text` and `tool_calls.tool_input`. `0001` to `0008` get their released SQL back (comments may differ), `0003_embeddings_hnsw_index.sql` returns under its own name, and a `make ci` and CI gate fails when a released migration's SQL differs from the latest release tag. A frozen version-9 schema file outside the migrations folder creates new warehouses at an explicit `v2.0.0` storage version, under a temp name renamed into place under the writer flock, with one `schema_version` row naming it, then migrates them forward. A test keeps it equal to the chain at version 9, apart from compression. A warehouse at schema 3 to 8 migrates to the head without `vss`; one below schema 3 stops with an error that names the file and says to move it aside. Old-file builders load `vss` only in a separate process. Docs and `memory-bank` describe the schema file and the immutability rule. The new-warehouse path runs once on this machine's real transcripts in a scratch home. Milestones 1 to 3 make the first release.

**Complexity:** Level 3

## 2026-10-22 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Cleared the L4 preflight status file (its findings are folded into `milestones.md` and `projectbrief.md`)
    - Classified milestone 3, "Restore every released migration as it shipped and create new warehouses from a frozen schema file in DuckDB 2.0's storage format with ZSTD on messages.text and tool_calls.tool_input"
* Decisions made
    - Level 3, as the L4 re-plan estimated. Most of the restoration copies files back from `main`. The new code is the schema file and its equality test, the create path with temp-then-rename, the stop rule, and the immutability gate. All of it sits in the warehouse creation and migration subsystem
