# Current Task: dashboard-md-backslash-escape

**Complexity:** Level 1

## Fix

- **What broke:** Session pills rendered Cursor backslash paths as `SumMem.cursor` instead of `SumMem\.cursor`.
- **Why:** markdown-it applies CommonMark backslash-escapes; `.` is punctuation, so `\.` becomes `.`.
- **What changed:** `bindSessionMarkdown` disables markdown-it's `escape` rule (not a plugin). Bold/code still render. Warehouse/ingest untouched.
- **Files:** `dashboard-session.mjs`, `dashboard.mjs`, `tests-js/dashboard-session.test.mjs`

## Verification

- [x] Failing test reproduced `SumMem.cursor`; disable-escape made it pass
- [x] `make test` in this worktree: JS 121 passed; pytest 821 passed, 4 skipped
- [ ] Live dashboard on :58008 deferred — another worker owns that process
