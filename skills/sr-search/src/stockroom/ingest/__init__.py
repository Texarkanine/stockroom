"""The stockroom trace-ingest (ETL) subsystem.

Fills the milestone-1 DuckDB schema from the operator's own Cursor and Claude
Code history, writing through the milestone-2 ``warehouse.open()`` chokepoint.
The pipeline is, per harness, per run:

    sources (discover + watermark) -> cursor.py / claude.py (clean-room parse
    -> model.NormalizedSession) -> writer (delete-then-insert by
    (harness, session_id)) -> _sync_state watermark update

with an optional ``enrich`` step that folds Cursor ``ai-code-tracking.db``
model/labeling fields in when that DB is present.

The orchestrator entrypoint :func:`ingest` is added in a later build step; this
package module currently only anchors the subpackage.
"""
