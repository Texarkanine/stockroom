# Task: dashboard-marathon-link-and-msg-deep-link-investigate

* Task ID: dashboard-marathon-link-and-msg-deep-link-investigate
* Complexity: Level 2
* Type: simple enhancement + investigation

Make the Wrapped "Marathon Session" cell a deep-link to that conversation, and decide (via investigation) whether/how to add message-ordinal hash deep-links on reconstruction bubbles.

## Investigation Findings: Message Ordinal Deep-Links

**Verdict: feasible and straightforward.** No backend gap.

Evidence:
- `session_detail` already returns `ordinal` on every message (`metrics.py` / existing test asserts `[0, 1]`).
- `renderSessionDetail` in `dashboard.mjs` builds `<article class="session-turn …">` but does not set `id`, show ordinal, or read `location.hash`.
- Session deep-links already use query params (`?view=session&harness=&session=`); `buildSessionDeepLink` currently clears `url.hash`.
- Session load is async (`openSessionView` → fetch → `renderSessionDetail`), so native browser hash scroll on first paint will miss — need post-render scroll.
- Toolbar is not `position: sticky`; anchoring to the top of the bubble with `scrollIntoView({ block: "start" })` (plus modest `scroll-margin-top` for breathing room under the page chrome) meets "anchor to TOP of bubble."

Recommended approach (if implemented this task):
- Element id: `msg-{ordinal}` (e.g. `id="msg-0"`); hash `#msg-0`.
- Visible ordinal indicator on each bubble (compact, clickable / copyable link to `#msg-N`).
- After `renderSessionDetail`, if `location.hash` matches `/^#msg-(\d+)$/`, `scrollIntoView({ block: "start" })` on that article.
- Extend `buildSessionDeepLink(baseUrl, harness, sessionId, { ordinal }?)` to append `#msg-N` when provided; keep clearing unrelated hashes.
- On hashchange while already on the session view, re-scroll (no refetch).

**Scope gate:** Operator confirmed **both** (2026-07-27) — marathon link + ordinal Steps 5–7 are in this build.

## Test Plan (TDD)

### Behaviors to Verify

**Marathon (in scope)**
- Marathon payload with identity: `wrapped()` marathon winner → `marathon_session` includes `session_id` and `harness` (plus existing fields).
- Empty warehouse: `marathon_session` is `null` / no link fields.
- Wrapped cell model: when harness + session_id present → marathon cell exposes `href` built like session deep-link query (`view=session&harness&session`); when missing → no `href`, value remains `—`.
- Render: `renderWrapped` emits an `<a>` for the marathon value (or cell) when `href` is set; other cells stay plain text.
- Regression: other wrapped cells unchanged; subtitle/title hover behavior preserved.

**Ordinal deep-links (only if scope approved)**
- Bubble render: each turn article gets `id="msg-{ordinal}"` and a visible ordinal control whose `href` is `#msg-{ordinal}`.
- Post-render scroll: after detail render with `location.hash === "#msg-N"`, target article is scrolled with block=start.
- Deep-link builder: optional ordinal appends `#msg-N`; without ordinal, no hash (current behavior).
- Missing ordinal / unknown hash: no throw; no scroll.
- Hashchange on same session: scrolls to new target without refetch.

### Test Infrastructure

- Framework: pytest (`skills/sr-search/tests/`) + Node 22 test runner (`skills/sr-search/tests-js/`, `make test-dashboard-js`)
- Test location: `tests/test_dashboard_metrics.py`, `tests-js/dashboard-core.test.mjs`, `tests-js/dashboard-session.test.mjs`; optionally `tests/test_dashboard_static.py` for HTML/CSS contracts
- Conventions: pytest functions `test_*` with seeded DuckDB; JS `node:test` + `node:assert/strict` importing pure helpers from static modules
- New test files: none expected (extend existing)

## Implementation Plan

Each step is one TDD cycle: **(a) write/extend failing test → (b) run and confirm fail → (c) implement → (d) run and confirm pass**. Do not start (c) before (b).

1. **API: include marathon `session_id`**
   - Files: `skills/sr-search/tests/test_dashboard_metrics.py`, `skills/sr-search/src/stockroom/dashboard/metrics.py`
   - (a) Extend `test_wrapped_returns_all_time_rollups_and_ignores_selector` expected `marathon_session` with `"session_id": "a1"`.
   - (c) In `wrapped()`, add `"session_id": row[1]` to the marathon dict.

2. **Pure cell model: marathon session identity for linking**
   - Files: `skills/sr-search/tests-js/dashboard-core.test.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`
   - (a) Assert marathon cell exposes `sessionHref` fields (`harness` + `sessionId`) when both present; omit when missing / empty warehouse.
   - (c) In `buildWrappedPanel`, set those fields from `marathon.harness` / `marathon.session_id`. **Do not import session URL helpers into core** (keep URL assembly in `dashboard.mjs`, which already imports `dashboard-session.mjs`). Preflight confirmed `dashboard-core.mjs` and `dashboard-session.mjs` are both currently import-free — still avoid coupling core to URL shape.

3. **DOM: render marathon as link + SPA navigation**
   - Files: `skills/sr-search/tests/test_dashboard_static.py` (and/or JS if a pure render helper is extracted), `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, `index.html` CSS if needed
   - (a) Contract test: `dashboard.mjs` builds marathon value as `<a>` using `buildSessionViewSearchParams` / `openSessionView` when identity present.
   - (c) In `renderWrapped`, when identity present: `<a href="?view=session&…">` with value text; same-tab click `preventDefault` + `openSessionView` (preserve middle-click/new-tab via real `href`). Style link inside `.wrapped-value` to match Wrapped chrome.

4. **Pure helpers: message anchor id + hash parse + deep-link ordinal**
   - Files: `skills/sr-search/tests-js/dashboard-session.test.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard-session.mjs`
   - (a) Tests for `messageAnchorId(ordinal) → "msg-N"`, `parseMessageHash("#msg-3") → 3` / invalid → null, `buildSessionDeepLink(..., { ordinal: 3 })` appends `#msg-3`, without ordinal clears/omits hash (current behavior).
   - (c) Implement those helpers; extend `buildSessionDeepLink` with optional ordinal option (prefer options object over 4th positional if it keeps call sites clean — update existing call sites/tests).

5. **Ordinal indicators + bubble ids**
   - Files: `skills/sr-search/tests/test_dashboard_static.py`, `dashboard.mjs` (`renderSessionDetail`), `index.html`
   - (a) Static contracts: `msg-` / `messageAnchorId` / ordinal link class present; CSS includes `.session-turn { scroll-margin-top: … }` and ordinal indicator styles.
   - (c) Set `turn.id` from `messageAnchorId(message.ordinal)`; add visible `<a class="session-turn-ordinal" href="#msg-N">` (or similar); CSS for indicator + scroll-margin (top-of-bubble framing).

6. **Hash scroll after load + hashchange**
   - Files: `skills/sr-search/tests-js/dashboard-session.test.mjs` (pure resolve helper), `dashboard.mjs`
   - (a) Test pure `resolveMessageAnchorElement(root, hash)` (or equivalent) returns the `#msg-N` node / null.
   - (c) After successful `renderSessionDetail`, scroll match with `scrollIntoView({ block: "start" })`; on `hashchange` while in session view, re-scroll without refetch. Respect active-session gate so stale loads do not scroll.

7. **User-facing docs**
   - Files: `docs/user-guide/dashboard.md`
   - (a/c) Document optional `#msg-{ordinal}` on session deep-links; note Wrapped Marathon Session opens that conversation. No separate test file — doc change reviewed in QA.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing session deep-link contract: `?view=session&harness=&session=`
- Existing `session_detail.messages[].ordinal`
- Marathon SQL already selects `s.session_id` (row[1]) — only omitted from JSON today

## Challenges & Mitigations

- **Missing `session_id` in current API**: Already identified; Step 1 adds it. Mitigation: exact assertion update in wrapped pytest.
- **URL knowledge in core**: Mitigated — cell exposes `harness`/`sessionId` only; `dashboard.mjs` builds `href` + SPA click (preflight: both helper modules are import-free today; still keep URL assembly out of core).
- **Full page reload on marathon click**: Mitigated — real `href` for open-in-new-tab + `preventDefault`/`openSessionView` for same-tab SPA (matches sessions-row navigation feel).
- **Async hash scroll race**: Scroll only after messages are in the DOM; ignore stale requests via existing `sessionRequestGate` / `isActiveSessionView`.
- **Ordinal gaps / non-contiguous ordinals**: Use stored `message.ordinal`, not array index, so ids stay stable with warehouse identity.

## Pre-Mortem

- **Plan failed because marathon linked project/harness but not a specific session**: Addressed by requiring `session_id` in API + href; do not link on harness alone.
- **Plan failed because native `#fragment` scrolled before bubbles existed**: Covered by post-render scroll step; do not rely on browser default alone.
- **Plan failed by implementing ordinals without operator buy-in on hash shape / UI chrome**: Resolved — operator chose **both**.

## Preflight Amendments

- Encoded explicit test-before-code substeps on every implementation unit (was blocking TDD-encoding gap).
- Marathon cell carries identity fields; URL/`<a>` assembly stays in `dashboard.mjs`.
- Same-tab SPA navigation via `openSessionView` while keeping real `href`.
- Added `docs/user-guide/dashboard.md` update for `#msg-{ordinal}` + marathon link.
- Un-gated ordinal steps (operator confirmed both).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Investigation (ordinal deep-links) complete — feasible; approach proposed
- [x] Operator confirmation: include ordinal Steps 5–7 in this build? (both)
- [x] Preflight
- [ ] Build
- [ ] QA
