# Active Context

## Current Task: warehouse-file-growth, milestone 1 (drop the HNSW index and vss)
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY; operator review folded)

## What Was Done
- L4 re-entry: the operator reviewed the 7-milestone plan and ran `/niko`. Classified milestone 1 as Level 3
- Wrote the Level 3 plan in `tasks.md`: 6 steps, 16 behaviours, no open questions
- Decisions (from measurements on read-only copies of this machine's data):
    - One exact search statement: nearest chunk per owner, cut, then join text. 220 ms on 1.5.4 and about 160 ms on 2.0.0 for top-100 over 133,793 vectors. Today's scoped SQL takes 1.7 s and about 2 s
    - No orphan guard in the ranking (operator confirmed after preflight; see below). An orphan is left out, never raised
    - `0003` is renamed `0003_retired.sql` and holds only comments. `0009_drop_vector_index.sql` drops the index
- Found a hazard the milestone text understated: the live shim runs this checkout's working tree, so a file is live as soon as it is saved, committed or not. On 1.5.4 without `vss`, every write to `embeddings` fails while the index exists. So `0009` lands only after a live-copy proof, together with the `ensure_vss` removal, then `stockroom migrate` runs on the live warehouse at once. No stub `0009` may ever exist in this checkout
- Thirteenth preflight: PASS WITH ADVISORY (`.preflight-status`). The plan was not changed
- Operator decisions on the preflight (2026-10-22):
    - Orphan guard (advisory 3): **no guard**. The plan's reason was overstated. `write_session` runs without a transaction: it deletes a session's `messages` and re-inserts them, each statement committing on its own. So a crash in between leaves orphans until the next ingest or embed, and a top-k search can be short in that window. The operator accepts that over the guard's cost (+57 ms on 2.0.0, +340 ms on 1.5.4)
    - Build location (radical advisory): **in place**, in this checkout, not in a git worktree. With advisory 1's order (write `0009` first, then remove the `ensure_vss` calls, then the function), no landing moment is unsafe
    - Correction advisories 1, 2, 4, 5, 6, 7: the operator reviewed them and accepted all six. Folded into `tasks.md`: in step 4, `0009` is written first, then the `ensure_vss` calls, then the function; B12 moved to the retire-`0003` step; `test_schema_0007._apply_through` added to the `ensure_vss` cleanup; the live before record is taken just before landing (new step 4.5); full scratch-script paths added; and the shadow strip now runs before retiring `0003` (steps 2 and 3 swapped)
    - The orphan reasoning in `tasks.md` was corrected to match the no-guard decision
    - Advisory 8 (for milestone 3): v2.1.2's `0001` will be needed in the old-chain test builder once `0001` gains zstd; carry it into milestone 3's plan

## Next Step
- The operator runs `/niko-build`
