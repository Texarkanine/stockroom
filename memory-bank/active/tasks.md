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

## QA — PASS

- Confirmed `bindSessionMarkdown` is the only markdown-it instance in the dashboard (no sibling instance missed the fix); `renderSessionMessageHtml` is its sole call site.
- Independently re-ran `node --test tests-js/dashboard-session.test.mjs` (25/25) and `make test-dashboard-js` (121/121) worktree-local, without touching `make sync`/torch, the shim, or :58008.
- Probed the vendored parser directly with `escape` disabled: bold/italic/code/links/fenced code/space hard-breaks are unaffected; the only losses are literal `\`-newline hard breaks and `\*text\*` emphasis-suppression — both are the class of backslash-escape the fix is intentionally removing, and are outside the acceptance criteria.
- JSDoc style (double-backtick RST convention) and import placement match established file conventions; no plugins added, no ingest/warehouse touched.
- No stray debug artifacts, TODOs, or magic numbers in the diff. Doc updates confined to memory-bank (appropriate for a Level 1 display fix); no docs/systemPatterns.md gap identified.
