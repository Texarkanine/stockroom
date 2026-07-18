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

**Selected**: C — Two `panel-wide` stacked areas (conversation + message)

**Rationale**: Answers the issue’s “one or two charts?” with a clear dual-grain yes, matches #67’s presentation decision, uses the reserved `panel-wide` class, and avoids mixing incompatible Y units or inventing a toggle.

**Tradeoff**: Extra vertical space. Acceptable; empty periods collapse via existing no-data pattern.

## Implementation Notes

- Titles: `Model Usage over Time (by conversation)` and `Model Usage over Time (by message)`.
- Chart type: Chart.js `line` datasets with `fill: true`, stacked x/y scales, `tension` aligned with Write/Read (~0.3) unless readability needs zero tension.
- Colors: stable per-model color from shared palette (rank or model-name hash — prefer **global model color map** shared with top-models bars so color means the same model across panels).
- Series set: union of models that appear in the grain for the window; omit all-zero models; cap/top-N only if clutter demands (default: all models with any count; revisit if tests show noise — prefer no arbitrary top-10 unless proven).
- Bucketing: reuse `_trend_granularity` / `_date_labels` / `_week_labels` with the same window as other 30-day panels (or trends’ adaptive grain if that helper already chooses daily vs weekly from span).
- Aggregate: one stack (sum selected harnesses); Compare: either (1) separate harness stacks are too heavy — prefer **aggregate-only stacks with harness filter applied upstream** (selected harnesses summed), matching “area = attention” rather than harness×model matrices. Pin: Compare mode filters which harnesses contribute to the stack; does **not** add a harness dimension to the area chart (models remain the stack series).
- Place both wide panels immediately after the top-models pair.
- a11y: labeled canvases; legend from Chart.js; empty states when no attributed data.
