# Progress

Add a Cursor `beforeSubmitPrompt` trimmed non-blocking shim-rectify suspenders path (keep `sessionStart`; no `workspaceOpen`), and improve dashboard recovery UX so users get shim-first / replace guidance — or at least a pretty troubleshooting page — instead of bare JSON 404s after plugin updates.

**Complexity:** Level 3

## 2026-07-30 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Clarified intent: beforeSubmitPrompt = rectify-only, keep sessionStart, defer workspaceOpen
    - Clarified dashboard recovery: prefer detect shim-needs-rectify vs needs-replace; never advise `--replace` when shim is the problem; pretty troubleshooting fallback OK
    - Determined Level 3 (multi-component: hooks packaging + trimmed heal path + dashboard recovery UX; design decisions required)
* Decisions made
    - Level 3 Intermediate Feature
    - Claude / workspaceOpen out of scope for this task
* Insights
    - Cursor docs: `sessionStart` is fire-and-forget; `beforeSubmitPrompt` can gate send — non-blocking design is load-bearing
    - Full sessionStart payload on every submit was rejected; rectify-only suspenders + keep dashboard on sessionStart
