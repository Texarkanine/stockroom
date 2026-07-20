# Current Task: fix-dashboard-replace-macos-75

**Complexity:** Level 1

## Fix

- **What broke:** `verify_owned` only read `/proc/{pid}/cmdline`. On Darwin (no `/proc`) it always returned `False`, so replace/stale-identity kill was skipped.
- **Why:** Linux-only ownership probe treated missing `/proc` as “never owned.”
- **What changed:** Portable cmdline read — `/proc` first, then `ps ww -p <pid> -o args=`; still require `stockroom.dashboard` in cmdline. Identity + SIGTERM-only-recorded-pid unchanged.
- **Files:** `skills/sr-search/src/stockroom/dashboard/__main__.py`, `skills/sr-search/tests/test_dashboard_cli.py`

## QA

- **Result:** PASS
- **Findings:** None blocking. Portable helpers are minimal and match the issue’s `/proc` + `ps` contract; no new deps/protocol; identity/kill path untouched; no-`/proc` regression present; no doc debt.
