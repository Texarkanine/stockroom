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

1. **API: include marathon `session_id`**
   - Files: `skills/sr-search/src/stockroom/dashboard/metrics.py`, `skills/sr-search/tests/test_dashboard_metrics.py`
   - Changes: In `wrapped()`, add `"session_id": row[1]` to `marathon_session` dict. Update `test_wrapped_returns_all_time_rollups_and_ignores_selector` expected dict (`session_id: "a1"` for the 5-message claude winner).

2. **Pure cell model: marathon `href`**
   - Files: `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`, `skills/sr-search/tests-js/dashboard-core.test.mjs`
   - Changes: In `buildWrappedPanel`, when `marathon.harness` and `marathon.session_id` are present, set `href` via `buildSessionViewSearchParams` / relative query string (reuse `dashboard-session.mjs` helper — import if layering allows, or duplicate the three-param query construction only if import would create a cycle; prefer import). Empty/missing → no `href`.

3. **DOM: render marathon as link**
   - Files: `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, CSS in `index.html` if needed for link styling inside `.wrapped-value`
   - Changes: In `renderWrapped`, when `cell.href` is set, put an `<a href="…">` (value text) instead of plain text. Prefer real navigation (works with boot URL parse; middle-click/new tab). No click-handler SPA detour unless full reload proves jarring — real `<a>` is the product "link."

4. **Docs (light)**
   - Files: only if user-facing dashboard docs mention Wrapped cells; otherwise skip. Prefer code/tests as SSOT for this micro-UX.

5. **[GATED] Ordinal indicators + hash ids**
   - Files: `dashboard.mjs` (`renderSessionDetail`), `index.html` (styles for ordinal indicator / `scroll-margin-top` on `.session-turn`), tests in `dashboard-session.test.mjs` and/or new pure helper tests
   - Changes: Set `turn.id = \`msg-${message.ordinal}\``; add ordinal link UI; CSS `scroll-margin-top` for top-of-bubble framing.

6. **[GATED] Hash scroll after load + hashchange**
   - Files: `dashboard.mjs` (`openSessionView` / `renderSessionDetail`), optionally extract `scrollToMessageHash(hash)` pure-adjacent helper into `dashboard-session.mjs` for testability
   - Changes: After render, scroll if hash matches; listen for `hashchange` while in session view.

7. **[GATED] Deep-link helper accepts optional ordinal**
   - Files: `dashboard-session.mjs`, `tests-js/dashboard-session.test.mjs`
   - Changes: `buildSessionDeepLink(..., ordinal?)` appends `#msg-N`; copy-link button can stay session-only unless we later wire "copy message link" from the ordinal control (`href` already sufficient for copy-link-address).

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing session deep-link contract: `?view=session&harness=&session=`
- Existing `session_detail.messages[].ordinal`
- Marathon SQL already selects `s.session_id` (row[1]) — only omitted from JSON today

## Challenges & Mitigations

- **Missing `session_id` in current API**: Already identified; Step 1 adds it. Mitigation: exact assertion update in wrapped pytest.
- **Import cycle `dashboard-core` ↔ `dashboard-session`**: Check imports before wiring; if cycle, put a tiny `buildSessionViewSearchParams` call site string in core or move href assembly to `renderWrapped` in `dashboard.mjs` (which already imports session helpers). Prefer assembling `href` in `dashboard.mjs` from cell `{ harness, sessionId }` if that keeps core free of session URL knowledge.
- **Async hash scroll race**: Scroll only after messages are in the DOM; ignore stale requests via existing `sessionRequestGate` / `isActiveSessionView`.
- **Ordinal gaps / non-contiguous ordinals**: Use stored `message.ordinal`, not array index, so ids stay stable with warehouse identity.

## Pre-Mortem

- **Plan failed because marathon linked project/harness but not a specific session**: Addressed by requiring `session_id` in API + href; do not link on harness alone.
- **Plan failed because native `#fragment` scrolled before bubbles existed**: Covered by post-render scroll step; do not rely on browser default alone.
- **Plan failed by implementing ordinals without operator buy-in on hash shape / UI chrome**: Scope gate above — Build omits Steps 5–7 until operator confirms.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Investigation (ordinal deep-links) complete — feasible; approach proposed
- [x] Operator confirmation: include ordinal Steps 5–7 in this build? (both)
- [ ] Preflight
- [ ] Build
- [ ] QA
