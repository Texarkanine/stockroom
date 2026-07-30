# Active Context

**Current Task:** cursor-beforesubmit-shim-rectify-and-dashboard-recovery-ux
**Phase:** BUILD - COMPLETE
**What Was Done:**
- Shim: `rectify(..., ensure_env=False)` + CLI `--path-only`
- Cursor `beforeSubmitPrompt`: continue-first + background path-only rectify (timeout 10); `sessionStart` unchanged
- `dashboard/recovery.py`: one in-memory diagnostic HTML page (shim-first ordered remedies + troubleshooting links)
- Server: static/document misses → HTML recovery; `_not_found()` stays JSON for API/session
- Docs: lifecycle, dashboard, troubleshooting
- Verification: `make test` 793 passed / 4 skipped + 119 JS; `make lint` clean

**Deviations:** None — built to MVP plan (no classifier).

**Next Step:** QA (`/niko-qa` will run automatically per L3 workflow).
