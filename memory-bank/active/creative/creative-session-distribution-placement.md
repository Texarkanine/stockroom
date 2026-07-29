# UI/UX Decision: Session Distribution Placement

## User & Context

**Users:** Local stockroom operators reviewing a single reconstructed conversation on the dashboard (`?view=session`). Same persona as the rest of the offline metrics UI — technical, ADHD-friendly density OK if hierarchy is clear.

**Task:** At a glance, understand how this conversation spent agentic effort across tools and skills (part-to-whole), then continue reading the transcript.

**Context:** Appears on the session overview after title/meta, before or beside the turn list. Metrics pane already teaches doughnut language for tools/skills globally; session view today is meta + chat only inside a `min(1200px)` centered column with no side rail.

**Constraints:** Offline/no CDN; vendored Chart.js; match dashboard CSS tokens; preserve deep links (`#msg-N`); empty sessions must degrade gracefully; operator must visually pick placement.

## Design System

Authority: shipped dashboard static surface (`skills/sr-search/src/stockroom/dashboard/static/` — tokens in `index.html`, Chart.js doughnuts via `dashboard-core.mjs`). Mockups reuse those CSS variables.

## Options Evaluated

- **A · Side column**: Sticky ~240px rail beside the transcript with Tools + Skills doughnuts + legends. Charts stay visible while scrolling; chat column narrows.
- **B · Inline above**: Full-width summary band under session meta, above turns. Preserves full chat width; scrolls away with content.
- **C · Popover / disclosure**: Collapsed “Tool & skill composition” control near meta; expands to dual doughnuts on demand. Minimal permanent chrome.
- **D · Header dials** (internet prior art): Compact dual doughnuts + totals in a header band under meta — pattern seen in conversation usage header stats ([PocketDev #231](https://github.com/tetrixdev/pocket-dev/issues/231), [AgentsView session header](https://agentsview.io/usage/)). Branch name `per-convo-dials` foreshadows this. At-a-glance without a permanent side rail; legend/detail can be progressive.

**Mockups (open in browser):** [`mockups-session-distribution.html`](./mockups-session-distribution.html)

```bash
# from repo root
xdg-open memory-bank/active/creative/mockups-session-distribution.html
# or: open / file://… on macOS
```

## Analysis

| Criterion | A Side | B Inline | C Popover | D Header dials |
|-----------|--------|----------|-----------|----------------|
| Usability (glance while reading) | High while scrolling | High at open; lost when scrolled | Low until open | High at open; compact |
| Clarity (hierarchy) | Strong separation | Strong band | Hidden until expand | Strong if totals labeled |
| Accessibility | Sticky aside OK if labeled | Straightforward landmark | Needs button/details semantics | Compact — legend via expand/tooltip |
| Consistency w/ metrics doughnuts | High | High | High | High (smaller) |
| Feasibility | Medium (new grid; mobile stack) | Easy | Easy | Easy–medium |
| Simplicity | Extra column forever | Always-on chrome | Least chrome | Light always-on chrome |
| Design system adherence | Fits tokens; new layout mode | Fits | Fits | Fits; matches meta band |

Key insights:
- Prior art for *per-conversation* usage favors **header/stats band** more than a permanent analytics sidebar (sidebars more common when the product is support/observability with many metadata tabs).
- Long tool names make pure pie legends cramped in a narrow rail — metrics already use doughnut + legend; same risk in A.
- Operator asked for visual pick among A/B/C and openness to a better pattern → D is that candidate, not a silent winner.

## Decision

**Low-Confidence Result**: Placement is a taste/attention-budget call the operator must make by looking at the mockups. No clear winner from criteria alone — A wins persistence-while-scrolling, B/D win simplicity and prior-art alignment, C wins minimalism.

**Recommendation (non-binding):** Prefer **D (header dials)** if the goal is “see composition without shrinking the transcript,” with optional expand for full legends; fall back to **B** if dual medium doughnuts + legends feel more readable than mini dials. Avoid A unless sticky visibility while reading long threads is the top priority.

## Implementation Notes

Deferred until operator selects A/B/C/D (or a hybrid). Regardless of placement:
- Reuse Chart.js doughnut patterns from metrics (`buildToolsPanel` / skills nested or a session-scoped dual doughnut).
- Cap categories (top N + Other) per donut best practice.
- Hide or show empty-state copy when a session has zero tools/skills.
