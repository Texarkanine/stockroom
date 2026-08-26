---
task_id: dashboard-md-backslash-escape
complexity_level: 1
date: 2026-08-26
status: completed
---

# TASK ARCHIVE: dashboard-md-backslash-escape

## SUMMARY

Dashboard session pills collapsed Cursor backslash paths such as `SumMem\.cursor` into `SumMem.cursor`. Warehouse and Cursor JSONL still had the backslash. `bindSessionMarkdown` now disables markdown-it's CommonMark `escape` rule so hidden-dot segments survive render. Ready PR: [#123](https://github.com/Texarkanine/stockroom/pull/123).

## REQUIREMENTS

1. Keep `.cursor` (and other hidden-dot segments) visible in session reconstruction.
2. Change only the render path; no warehouse or ingest rewrite.
3. Smallest durable fix that covers the whole punctuation-after-backslash class, not a `.cursor` special case.
4. Do not add a markdown-it plugin; do not stomp the shared shim or the other worker's `:58008` dashboard.

## IMPLEMENTATION

`bindSessionMarkdown` calls `markdown.disable("escape")` and returns `markdown.render`. `dashboard.mjs` uses that binder for session bodies. No path regex, no preprocess (a naive backslash-doubler would corrupt fenced code). Bold, italic, code, links, and fences still render.

Key files: `skills/sr-search/src/stockroom/dashboard/static/dashboard-session.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, `skills/sr-search/tests-js/dashboard-session.test.mjs`.

## TESTING

- TDD: the new JS test failed on `SumMem.cursor` against the vendored parser, then passed after the disable. Also asserts `.git` and `**bold**`.
- Worktree `make test`: 121 JS passed; 821 pytest passed, 4 skipped.
- QA PASS (Claude Sonnet). Completeness: this is the dashboard's only markdown-it instance; `renderSessionMessageHtml` is its sole call site.
- Live UI: worktree dashboard on `:58009` (left `:58008` alone) showed `#msg-0` of `604ead72-0402-49f2-bceb-c22ebed2ec33` as `SumMem\.cursor`. Operator confirmed.

## LESSONS LEARNED

Cursor already emits Windows `\` separators for WSL Unix paths; `.cursor` is in the source. The only display loss was CommonMark treating `\.` as an escape. Configuring the parser beats preprocessing.

## PROCESS IMPROVEMENTS

Level 1 has no archive phase; this document exists because the operator invoked `/niko-archive` after the L1 wrap-up. Parallel worktrees share one shim and one `:58008` — validate on a spare port.

## TECHNICAL IMPROVEMENTS

None for this render path. Cursor still writes backslash paths; that is upstream presentation, not a Stockroom store bug.

## NEXT STEPS

Land [#123](https://github.com/Texarkanine/stockroom/pull/123). Worktree-local `:58009` can be stopped; do not restart `:58008` for the other worker.
