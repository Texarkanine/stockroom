# UI/UX Decision: Session Distribution Placement

## User & Context

**Users:** Local stockroom operators reviewing a single reconstructed conversation on the dashboard (`?view=session`). Same persona as the rest of the offline metrics UI — technical, ADHD-friendly density OK if hierarchy is clear.

**Task:** At a glance, understand how this conversation spent agentic effort across tools and skills (part-to-whole), then continue reading the transcript.

**Context:** Appears on the session overview after title/meta, before or beside the turn list. Metrics pane already teaches doughnut language for tools/skills globally; session view today is meta + chat only inside a `min(1200px)` centered column with no side rail.

**Constraints:** Offline/no CDN; vendored Chart.js; match dashboard CSS tokens; preserve deep links (`#msg-N`); empty sessions must degrade gracefully; operator must visually pick placement.

## Design System

Authority: shipped dashboard static surface (`skills/sr-search/src/stockroom/dashboard/static/` — tokens in `index.html`, Chart.js doughnuts via `dashboard-core.mjs`). Mockups reuse those CSS variables.

## Options Evaluated

- **A · Side column (revised)**: Sticky ~240px composition rail as a **sibling outside** the conversation card (page grid), not nested inside the message body. Charts stay visible; chat card narrows within the 1200px page.
- **B · Inline above**: Full-width summary band under session meta, above turns, inside the conversation card. Operator noted liking its simplicity. Scrolls away with content.
- **C · Slide-in drawer (revised “popover”)**: Sticky vertical handle on the **viewport’s right edge** that follows scroll; click slides in a higher-z panel from the right (empty wide-screen margin, or overlapping the conversation when narrow); « collapses it again. Not a `<details>` disclosure.
- **D · Header dials**: Dropped by operator — not desired.

**Mockups:** [`mockups-session-distribution.html`](./mockups-session-distribution.html) (serve over http for integrated browser; e.g. `http://127.0.0.1:8765/mockups-session-distribution.html`)

## Analysis

| Criterion | A Side (outside card) | B Inline | C Slide-in drawer |
|-----------|----------------------|----------|-------------------|
| Usability (glance while reading) | High while scrolling | High at open; lost when scrolled | On demand; handle always reachable |
| Clarity (hierarchy) | Card vs rail separation | Strong band | Conversation primary until open |
| Accessibility | Labeled sticky aside | Straightforward landmark | Focus trap / Esc / aria-expanded needed |
| Consistency w/ metrics doughnuts | High | High | High |
| Feasibility | Medium (page grid) | Easy | Medium (fixed handle + drawer) |
| Simplicity | Always-on second column | Always-on band (operator liked) | Least permanent chrome |
| Design system adherence | Fits tokens | Fits | Fits; new interaction pattern |

Key insights:
- First A mock nested the rail inside the message card — wrong; operator expects sibling outside the body.
- Operator’s “popover” meant edge-affordance + slide-over, not disclosure expand-in-place.
- D removed from consideration.

## Decision

**Low-Confidence Result**: Still awaiting operator visual pick among revised A / B / C. Soft lean toward **B** given operator’s simplicity comment, unless sticky-while-scrolling (A) or get-out-of-the-way (C) wins on second look.

## Implementation Notes

Deferred until operator selects A/B/C (or a hybrid). Regardless of placement:
- Reuse Chart.js doughnut patterns from metrics (`buildToolsPanel` / skills nested or a session-scoped dual doughnut).
- Cap categories (top N + Other) per donut best practice.
- Hide or show empty-state copy when a session has zero tools/skills.
- If C: keyboard dismiss, `aria-expanded` on handle, prefer `prefers-reduced-motion` for the slide.
