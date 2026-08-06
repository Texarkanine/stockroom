# Current Task: fix-dashboard-sessions-ellipsis-order

**Complexity:** Level 1

## Investigation

- **What broke:** Metrics Sessions panel below `… N more` listed the oldest end oldest-first (absolute oldest immediately under the ellipsis).
- **Why:** `/api/sessions_ends` selected the 10 oldest via `ORDER BY activity ASC` and returned that ASC wire order. The UI preserves API order, so the bottom block read oldest→newer while the top block is newest→older.
- **What changed:** Still select the 10 oldest with ASC, then reverse before return so `oldest` is DESC (newest→older reading continuity through the fold).
- **Files:** `skills/sr-search/src/stockroom/dashboard/metrics.py`, `skills/sr-search/tests/test_dashboard_metrics.py`
