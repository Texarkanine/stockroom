# Progress

Stop the warehouse file growing far past the history it holds, as specified in [issue 147](https://github.com/Texarkanine/stockroom/issues/147) and `memory-bank/active/projectbrief.md`. Keep HNSW, rebuild it around embedding writes, insert vectors through NumPy, create new warehouses in the current DuckDB storage format with ZSTD text columns, rewrite an existing warehouse once in verify-only mode, and teach read-only `stockroom doctor` to report the file. The swap that replaces the live file stays a separate change and stays off.

**Complexity:** Level 4

## 2026-10-20 - COMPLEXITY ANALYSIS - COMPLETE

* Work completed
    - Confirmed the issue is the spec, including the safety rules and the verify-only first release
    - Classified the work as Level 4
* Decisions made
    - Level 4 because the change crosses warehouse creation, embed writes, index lifetime, an automatic rewrite, and doctor, and a bad rewrite can lose the warehouse
    - Issue 147 supersedes the earlier creative note that dropped HNSW and added a `compact` command
* Insights
    - The approach is already decided in the issue. Planning only has to split it into milestones that can ship on their own
