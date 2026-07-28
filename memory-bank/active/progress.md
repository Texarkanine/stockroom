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

## 2026-07-27 - PLAN - COMPLETE

* Work completed
    - Wrote TDD + implementation plan for marathon session link
    - Investigated ordinal hash deep-links; documented findings in `tasks.md`
* Decisions made
    - Marathon requires adding `session_id` to `marathon_session` JSON (SQL already has it)
    - Prefer real `<a href="?view=session&…">` over SPA-only click handler
    - Recommended ordinal hash shape `#msg-{ordinal}` with post-render `scrollIntoView({ block: "start" })`
    - Ordinal implementation gated on operator confirmation before Build
* Insights
    - `session_detail` already returns per-message `ordinal`; gap is purely client render/navigation
    - Default browser hash scroll is insufficient because session messages render after async fetch

## 2026-07-27 - SCOPE CONFIRMATION

* Decisions made
    - Operator chose **both**: marathon Wrapped link + ordinal `#msg-N` deep-links in this build

## 2026-07-27 - PREFLIGHT - COMPLETE

* Work completed
    - Validated plan against codebase; wrote `.preflight-status` PASS
    - Amended plan for blocking TDD encoding + SPA link pattern + docs touchpoint
* Decisions made
    - Cell model exposes harness/sessionId; `dashboard.mjs` owns href + `openSessionView`
    - Document `#msg-{ordinal}` in `docs/user-guide/dashboard.md`
* Insights
    - `dashboard-core.mjs` and `dashboard-session.mjs` are currently import-free; still keep URL shape out of core
    - Session list rows are not `<a>` tags; marathon should be a real link with SPA progressive enhancement
