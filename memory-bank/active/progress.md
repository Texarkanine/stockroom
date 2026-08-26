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
