# Progress

Make the Wrapped Marathon Session cell a link to that conversation, and investigate whether message ordinal indicators can deep-link via URL hash to a specific bubble (anchored to the top of the bubble).

**Complexity:** Level 2

## 2026-07-27 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed intent with operator
    - Classified as Level 2 (self-contained dashboard enhancement + investigation)
* Decisions made
    - Marathon link is in scope to implement
    - Message ordinal deep-links are investigation-first; implement only if straightforward after agreement
* Insights
    - Session deep-links already exist (`view=session` query params + Copy deep-link); marathon cell currently has no `href`/navigation
    - No existing `location.hash` / message-anchor machinery in the dashboard static JS
