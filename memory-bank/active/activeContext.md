# Active Context

## Current Task: warehouse-file-growth
**Phase:** PREFLIGHT - COMPLETE (FAIL (fixable))

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

## Next Step
- Re-plan the milestone list. Waiting on the operator for the doctor fix name, and for whether embed drops the HNSW index before the orphan sweep
