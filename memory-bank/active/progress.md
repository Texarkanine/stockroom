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
