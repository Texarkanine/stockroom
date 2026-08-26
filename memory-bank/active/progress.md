# Progress

Fix session-view markdown rendering so Cursor backslash paths keep hidden-dot segments like `.cursor` instead of collapsing `\.` into the parent directory name. Display-only; warehouse and ingest stay untouched.

**Complexity:** Level 1

## 2026-08-26 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Validated intent: markdown-it backslash-escape of `\.` in session pills; bytes already correct in warehouse and Cursor JSONL.
    - Wrote project brief, active context, and task stub.
* Decisions made
    - Level 1: single-component display bug in the session message render path.
    - Shared-machine rule: do not touch the on-path `stockroom` shim or the live dashboard process owned by another worker; prefer worktree-local tests and defer live UI validation.
* Insights
    - Cursor emits Windows `\` separators for WSL Unix paths; the only lost glyph on screen is punctuation after `\`, which CommonMark treats as an escape.

## 2026-08-26 - BUILD - COMPLETE

* Work completed
    - Extracted `bindSessionMarkdown` and pointed session pills at it.
    - Disabled markdown-it `escape` so `\.` (and every other punctuation-after-backslash) survives; bold and code still render.
    - Added a JS test against the vendored markdown-it that failed on `SumMem.cursor` before the disable and passed after.
    - `make test` in this worktree: 121 JS passed; 821 pytest passed, 4 skipped.
* Decisions made
    - Disable the built-in rule rather than preprocess paths or add a plugin: one call, whole punctuation class, code fences stay literal.
    - Live :58008 and the on-path shim left alone for the other worker.
* Insights
    - A naive preprocess that doubles backslashes would corrupt fenced code; configuring the parser avoids that.

## 2026-08-26 - QA - COMPLETE (PASS)

* Work completed
    - Re-verified `bindSessionMarkdown` is the dashboard's one markdown-it instance and sole session-body call site.
    - Re-ran `node --test tests-js/dashboard-session.test.mjs` (25/25) and `make test-dashboard-js` (121/121) worktree-local; no `make sync`, torch, shim, or :58008 touched.
    - Probed the vendored parser with `escape` disabled: bold/italic/code/links/fenced code/space hard-breaks unaffected; only literal `\`-newline hard breaks and `\*text\*` suppression are lost, both within the intentionally-removed escape class and outside the stated acceptance criteria.
* Decisions made
    - No KISS/DRY/YAGNI/completeness/regression/integrity/documentation findings block acceptance. PASS.
* Insights
    - Import-list ordering in `dashboard.mjs` is only loosely alphabetized already; placing `bindSessionMarkdown` next to `renderSessionMessageHtml` matches existing drift, not a new violation.
