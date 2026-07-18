# UI/UX Decision: Top Models Presentation (#67)

## User & Context

**Users:** Local stockroom operators glancing at the metrics dashboard (offline, Aggregate/Compare).  
**Task:** See which models dominate by conversation count vs by message volume — different stories when one model runs marathons and another handles many short chats.  
**Context:** Replaces / extends the existing half-width “Top Models” horizontal bar beside Write/Read in the main `.chart-grid`.  
**Constraints:** Chart.js vendored; Aggregate/Compare harness stacking; keyboard/ARIA labels on canvases; no new SPA chrome beyond panel headers.

## Design System

Authority: shipped dashboard static surface (`skills/sr-search/src/stockroom/dashboard/static/` — `index.html`, `dashboard-core.mjs`, Chart.js bars). Half-width `.panel` in a 2-column `.chart-grid`; harness colors via existing palette helpers.

## Options Evaluated

- **A — Two side-by-side bars**: Replace one “Top Models” panel with “Top Models (by conversation)” and “Top Models (by message)” as two half-width horizontal bars (same `buildModelsPanel`-style encoding).
- **B — Single grouped/stacked bar**: One panel; each model row shows conversation and message as grouped bars or a dual metric — denser, needs a new encoding and legend story.
- **C — Toggle inside one panel**: One canvas; header control switches grain. Saves a cell; adds interaction the metrics grid mostly avoids outside Aggregate/Compare.

## Analysis

| Criterion | A Two panels | B Single dual-encode | C Toggle |
|-----------|--------------|----------------------|----------|
| Usability | High — glance both grains | Medium — decode encoding | Medium — extra click |
| Clarity | High — title carries grain | Lower — mixed scales risk | Medium — one grain at a time |
| Accessibility | Two labeled canvases (existing pattern) | One canvas, denser tooltip | Control + canvas |
| Consistency | Matches tools/skills half panels | Novel for this dashboard | Novel control |
| Feasibility | Clone panel + second series from API | New Chart.js options | New UI state |
| Design system | Best fit | Stretches bar pattern | Stretches shell |

Key insights:
- Issue #67 already leans toward “second graph, next to the existing… with clarification in each chart title.”
- Conversation vs message are different units — side-by-side avoids false dual-axis comparisons in one chart.
- Attribution creative already defines both grains; presentation should not collapse them.

## Decision

**Selected**: A — Two side-by-side bars with grain-clarified titles

**Rationale**: Matches the issue’s preferred framing, reuses the existing horizontal-bar panel model, and makes the dual-grain story readable without new interaction or scale mixing.

**Tradeoff**: Consumes an extra grid cell (Write/Read moves to the next free half-cell / reflow). Acceptable for clarity.

## Implementation Notes

- Titles: `Top Models (by conversation)` and `Top Models (by message)` (or equivalent short form pinned in static tests).
- Same range line (“Last 30 days”) and empty-state pattern as today’s models panel.
- Aggregate: one series each; Compare: harness-stacked like current `buildModelsPanel`.
- Rank each grain independently (top-N by that grain’s totals) — do not force a shared label axis unless creative later demands it; independent ranking best matches “different stories.”
- Place the pair as one grid row; keep Model Distribution ordering relative to Session Efficiency per existing static layout tests (update those pins).
- a11y: distinct `aria-label`s / canvas text fallbacks per panel.
