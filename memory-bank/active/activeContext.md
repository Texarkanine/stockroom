# Active Context

## Current Task: warehouse-file-growth, milestone 1 (drop the HNSW index and vss)
**Phase:** PLAN - COMPLETE

## What Was Done
- L4 re-entry: the operator reviewed the 7-milestone plan and ran `/niko`. Classified milestone 1 as Level 3
- Wrote the Level 3 plan in `tasks.md`: 6 steps, 16 behaviours, no open questions
- Decisions (from measurements on read-only copies of this machine's data):
    - One exact search statement: nearest chunk per owner, cut, then join text. 220 ms on 1.5.4 and about 160 ms on 2.0.0 for top-100 over 133,793 vectors. Today's scoped SQL takes 1.7 s and about 2 s
    - No orphan guard in the ranking: only `write_session` deletes `messages`, and it invalidates embeddings first. Live data has 0 orphans. A guard costs 2.5 times as much. An orphan is left out, never raised
    - `0003` is renamed `0003_retired.sql` and holds only comments. `0009_drop_vector_index.sql` drops the index
- Found a hazard the milestone text understated: the live shim runs this checkout's working tree, so a file is live as soon as it is saved, committed or not. On 1.5.4 without `vss`, every write to `embeddings` fails while the index exists. So `0009` lands only after a live-copy proof, together with the `ensure_vss` removal, then `stockroom migrate` runs on the live warehouse at once. No stub `0009` may ever exist in this checkout

## Next Step
- Level 3 preflight in a subagent
