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
- **E · Below conversation**: Conversation card ends; second full-width Tools & Skills container underneath with a 2-col chart grid echoing the metrics dashboard. Reached by scrolling past the transcript.
- **E-2 · Full-size above**: Same dashboard-scale Tools & Skills card as E, placed above the conversation card (B’s position, E’s size). Meta still inside the conversation card.
- **F · Split pills**: Session meta pill + Tools & Skills pill above; conversation card is **messages only** — no summary chrome in the transcript box.

**Mockups:** [`mockups-session-distribution.html`](./mockups-session-distribution.html) — `http://127.0.0.1:8765/mockups-session-distribution.html?v=4`

### Independent model picks (2026-07-29)

Unseeded (task + candidates + mockup URL only; no operator reasoning):

| Model | Pick | Runner-up |
|-------|------|-----------|
| GPT (`gpt-5.6-sol-high`) | **B** | A (persistent but costs width) |
| Opus (`claude-opus-5-thinking-high`) | **B** | A (sticky persistence unused for static aggregates; narrows primary content) |

Both framed composition as a once-on-entry summary that should not permanently tax the transcript.

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

**Selected**: **F · Overview + messages** (refined)

**Rationale**: Operator visual pick. Conversation card must not mix transcript with summary chrome. One overview pill + messages-only card.

**Structure**:
1. Overview pill — **no** “conversation overview” page header
2. **session** — the four metrics (harness, model, tokens, started)
3. **composition** — Tools & Skills charts only (no explanatory copy); same visual language as main metrics dashboard
4. Messages pill — conversation title (when present) as that card’s heading + transcript only
5. Copy / export toolbar — still choosing:
   - **F-a**: top of messages card (today’s order: toolbar → title → turns)
   - **F-b**: between overview pill and messages pill

**Tradeoff**: Charts scroll away with the overview (accepted; composition is glance-once). Drawer (C) and below-convo (E) rejected for this surface.

## Implementation Notes

- Reuse Chart.js doughnut / panel patterns from metrics (`buildToolsPanel`, skills nested or session-scoped dual doughnut) inside the overview pill under **composition**.
- Cap categories (top N + Other) per donut best practice.
- Empty sessions: hide composition section or show empty-state without broken charts.
- Split session UI: overview card (session metrics + composition charts) vs messages card (title + turns).
- Preserve copy deep-link / export markdown / export JSON; lock F-a vs F-b before build.
- Do not use sticky side rail (A), tiny inline-inside-card (B), slide-in drawer (C), or below-transcript-only (E) as the primary placement.
