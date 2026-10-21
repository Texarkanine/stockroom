# Active Context

## Current Task: warehouse-file-growth
**Phase:** PREFLIGHT - COMPLETE (PASS WITH ADVISORY)

## What Was Done
- Operator decision (2026-10-21): DuckDB 2.0 is the first milestone; there is no 2.0-only release. Milestones 1 to 8 ship in one release after the operator shadow-tests a branch clone on his Macs (not the work machine)
- Operator decision (2026-10-21): every release must stand alone, because users skip releases
- Operator decision (2026-10-21): new files and the copy use storage `v2.0.0` (not `v1.5.0`)
- Operator decision (2026-10-21): this checkout (the live engine here) stays on DuckDB 1.5.4 until the shadow test passes on this machine
- Operator decision (2026-10-21): the DuckDB 2.0 sub-run may rewrite DuckDB-behaviour sentences in later milestones
- Operator decision (2026-10-21): the DuckDB 2.0.0 HNSW replay bug gets no automatic repair. Doctor detects a leftover `.wal`; `stockroom doctor fix hnsw-wal` repairs it on request; a troubleshooting page documents it. Discoverable doctor commands never write; every doctor write sits behind `stockroom doctor fix <name>`
- Operator decision (2026-10-21): I drafted the upstream duckdb-vss issue; the operator files it
- Folded the eighth preflight's findings and advisories into `milestones.md` and `projectbrief.md`
- Ninth preflight (2026-10-21): FAIL (fixable). A DuckDB 2.0 replay can fold the `.wal` away and leave an HNSW index that silently lacks rows. The milestone list was not changed
- Operator decision (2026-10-21): the silent fold stays doctor-only. Doctor gains an index-coverage check. No repair on reconnect. The fix command is `stockroom doctor fix hnsw-rebuild`
- Operator decision (2026-10-21): about five installs, nightly embed, rollout is a couple of days. Build for a finished embed. A power loss may send the user to the troubleshooting page, and must not empty the warehouse. The HNSW index drops only around inserts. Ninth-preflight advisories, including opening `.warehouse.lock` without creating it, stay unadopted
- Folded the ninth preflight's finding into `milestones.md` and `projectbrief.md`. Still nine milestones, same order and graph
- Tenth preflight (2026-10-21): FAIL (fixable). A delete that removes `embeddings` rows, with the HNSW index left in place, leaks one index copy at checkpoint and at process close, on DuckDB 1.5.4 and 2.0.0
- Amended the "deletes leave the index in place" rule. A process that adds or removes rows drops the index, recreates it, and checkpoints before it exits. A delete that matches nothing is not a change. `stockroom doctor fix hnsw-rebuild` creates the index when it is already missing
- Eleventh preflight (2026-10-21): PASS WITH ADVISORY. The planned drop, delete, recreate, checkpoint cycle keeps used blocks flat on DuckDB 1.5.4 and 2.0.0. The milestone list was not changed
- Operator decision (2026-10-21): the growth test asserts used blocks, or a high-water file size of one index over the start, on every cycle. The one-index free-list alternation stays. No checkpoint while the index is down

## Next Step
- Advisory 2 is still open: ingest keeps the index down across every embedding delete in the process. `/niko` starts the first milestone
