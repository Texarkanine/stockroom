# UI/UX Decision: Model Usage Over Time (#68)

## User & Context

**Users:** Same dashboard operators as #67.  
**Task:** See, by color and area, how model mix shifts across the selected period — not only ranked totals.  
**Context:** New chart(s) in the metrics grid after the top-models row; issue suggests ~full (2-column) width.  
**Constraints:** Chart.js 4.x only (vendored); reuse trends date/week bucketing; attribution rules from `creative-dual-grain-attribution.md`; Aggregate/Compare already selects harnesses.

## Design System

Same static dashboard authority. `.panel-wide { grid-column: 1 / -1 }` exists but is unused on live panels — this feature is the natural first consumer. Existing time series: Daily Activity (bars), Write/Read (unfilled line). No prior stacked-area pattern — new Chart.js options on the shared render path (`line` + `fill` + stacked scales).

## Options Evaluated

- **A — One `panel-wide` conversation stacked area**: Full-width stack of session counts per model over time.
- **B — One `panel-wide` message stacked area**: Full-width stack of attributed assistant turns per model over time.
- **C — Two `panel-wide` stacked areas**: Conversation and message, each full width, titles clarifying grain (mirrors #67).
- **D — One `panel-wide` with grain toggle**: Single canvas; control switches conversation ↔ message.

## Analysis

| Criterion | A Conv only | B Msg only | C Both wide | D Toggle |
|-----------|-------------|------------|-------------|----------|
| Usability | Good overview | Better “attention” | Best parity with #67 | One grain at a time |
| Clarity | Clear | Clear | Clear if titled | Extra control |
| Consistency w/ #67 | Partial | Partial | Full dual-grain story | Partial |
| Feasibility | One new builder | One new builder | Two series + two panels | Builder + UI state |
| Simplicity | Best | Best | Slightly taller page | More shell complexity |
| Design system | Uses `panel-wide` | Uses `panel-wide` | Uses `panel-wide` ×2 | New control pattern |

Key insights:
- #67 already surfaces both grains as totals; #68’s job is the time dimension for those same grains.
- Conversation-only under-serves the “Composer all day” story; message-only under-serves multi-model Cursor presence over time.
- Toggle fights the dashboard’s mostly static panel inventory; Aggregate/Compare is enough global mode.
- Two wide charts are taller but scannable and keep units honest (sessions vs turns never share one Y-axis).

## Decision

**Selected**: A — One `panel-wide` conversation stacked area  
*(Operator amendment 2026-07-18 superseded C — see below.)*

**Rationale (original for C)**: Dual full-width areas mirrored #67.  
**Rationale (amended)**: Operator chose a single full-width “Model Usage over Time” under the two top-models bars. Conversation grain pairs with the left “as is” ranking chart; message grain remains the right-hand totals chart (#67) without a second time series.

**Tradeoff**: No message-grain area chart in v1 (Composer-all-day story is ranking-only on the right).

## Implementation Notes

- Title: `Model Usage over Time` (conversation grain; subtitle/range line can say sessions if needed).
- Chart type: Chart.js `line` datasets with `fill: true`, stacked x/y scales, `tension` aligned with Write/Read (~0.3) unless readability needs zero tension.
- Colors: stable per-model color from shared palette — **global model color map** shared with both top-models bars.
- Series set: models with any conversation-grain count in the window; no arbitrary top-10 unless clutter forces a follow-up.
- Bucketing: reuse `_trend_granularity` / `_bucket_labels` / `_activity_bucket`.
- Compare: harness filter applied upstream; stack series are **models only**.
- Grid placement: immediately under the top-models pair; then efficiency | first-prompt; then write/read `panel-wide`.
- a11y: labeled canvas; Chart.js legend; empty state when no data.

## Operator Amendment (2026-07-18)

Dashboard widget order locked by operator:

1. Left: Top Models (by conversation); right: Top Models (by message)
2. Full width: Model Usage over Time (one chart)
3. Session Efficiency | First-Prompt Quality (existing half panels)
4. Full width: Write / Read Ratio

Supersedes the earlier “two panel-wide model-trends” choice (option C).
