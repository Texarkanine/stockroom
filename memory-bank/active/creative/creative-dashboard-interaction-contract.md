# UI/UX Decision: Dashboard Interaction Contract

## User & Context

The user is the local stockroom operator: technically capable, interested in quickly understanding cross-harness activity, and already responsible for ingesting and maintaining the local warehouse. The dashboard is a read-only, at-a-glance surface opened in a browser from the local dashboard server. It must make the healthy path immediately legible while turning warehouse setup, schema, and lock failures into actionable guidance. It is a single-pane endpoint, not a navigation shell or analysis workbench.

## Design System

The visual authority is `planning/brainstorm/Cross-harness Warehouse (standalone).html`, interpreted through `planning/brainstorm/dashboard-spec.md`. The mock's centered 1200px surface, neutral cards, indigo accent, paired chart grid, gradient wrapped banner, and light/dark tokens establish the visual language. They are guides rather than pixel law: m1 API semantics, accessibility, the no-build/offline constraint, and explicit scope decisions take precedence.

## Options Evaluated

- **Contract-first native dashboard**: Preserve the mock's information hierarchy and visual language, but use native keyboard-accessible controls, one atomic fetch/render cycle, direct representations of every m1 field, and explicit global status handling.
- **Mock-faithful custom interaction**: Recreate the mock's custom checkbox dropdown, bespoke toggle, chart transitions, and decorative fields as closely as possible, including a client-derived "Your Type".
- **Panel-independent analytical console**: Let each panel fetch, fail, and refresh independently; prioritize partial availability and dense tabular fallbacks over a cohesive snapshot.

## Analysis

| Criterion | Contract-first native dashboard | Mock-faithful custom interaction | Panel-independent analytical console |
|---|---|---|---|
| Usability | One coherent snapshot; controls and failure actions are obvious | Familiar visual polish, but custom interaction behavior adds learning and failure modes | Partial results survive failures, but independent loading states make the page feel unstable |
| Clarity | Shipped API fields map directly to labels; mode and selection have distinct jobs | Decorative derivations such as "Your Type" blur measured data and interpretation | Mixed timestamps and independently refreshed panels weaken snapshot meaning |
| Accessibility | Native `details`, checkboxes, radio controls, semantic tables, live status, canvas labels/fallback summaries | Requires substantial custom keyboard, focus, and ARIA work | Strong table access, but the dense console compromises visual scanning |
| Consistency | Keeps the mock's layout, palette, cards, responsive pairing, and dark mode | Closest pixel resemblance | Diverges materially from the approved visual guide |
| Feasibility | Small vanilla HTML/CSS/JS surface with Chart.js UMD | Achievable, but more state and accessibility code without product value | Most asynchronous state and error plumbing |
| Simplicity | One state model, one selected harness set, one mode, one chart registry | Custom widgets and unsupported client personality mapping add concepts | Per-panel state machines are disproportionate for one local backend |

Key insights:

- Aggregate/Compare controls chart presentation, not metric meaning. KPI values should remain truthful summaries of the selected harness set in both modes.
- The server endpoints share one warehouse and are intended to form one dashboard snapshot. Atomic refresh with the previous successful snapshot retained is simpler and clearer than eight independent loading states.
- Native controls and semantic HTML recover most of the accessibility value without introducing a front-end framework or custom widget state machine.
- The mock's unsupported "Your Type" is not harmless decoration: deriving a personality from `top_tool` would turn an observed value into an undocumented judgment. Showing Top Tool preserves the eight-cell layout and the data contract.

## Decision

**Selected**: Contract-first native dashboard

**Rationale**: It delivers the approved visual hierarchy while staying faithful to m1, fully offline, framework-free, and keyboard usable. Every displayed fact has a direct source, the state model remains small, and actionable failures are visible without multiplying panel-level complexity.

**Tradeoff**: The harness selector will use a styled native disclosure/checklist rather than matching the mock's custom popup exactly, refreshes will be atomic rather than partially successful, and the wrapped banner will show Top Tool instead of the mock's speculative "Your Type".

## Implementation Notes

- Treat `overview.per_harness` as harness discovery. Sort raw harness keys alphabetically, assign the fixed positional palette, and derive display labels generically by splitting `_`/`-` and title-casing; never maintain a harness-name map.
- Default to every discovered harness selected and Aggregate mode. The selector uses a native `details` disclosure containing an All option plus labeled checkboxes. Prevent an empty selection. The Aggregate/Compare control is a radio group. Mode changes re-render the current snapshot; selection changes refetch the seven filterable endpoints with repeated `harness` parameters. Wrapped is fetched without a selector.
- Rely on endpoint-owned default windows and display their documented labels: overview/projects/tools/models/efficiency are 30 days, daily trends are 14 days, write/read trends are 12 weeks, sessions are recent-N, and wrapped is all time. Do not synthesize dates client-side or pass redundant bounds.
- Fetch all eight endpoints in parallel and commit the new snapshot only when all succeed. During first load, show a polite live status and stable placeholders. During refresh, keep the previous snapshot visible and mark the page busy. On failure, retain prior data if present and show a global `role="alert"` banner; surface the server's `action` text for 503 responses.
- Render zero KPIs, "No data in this period" chart summaries, an empty-table row, and nullable wrapped labels without throwing. No-data is distinct from a 503 warehouse refusal.
- Keep KPI semantics mode-independent. Sessions and messages sum selected harness values; Projects uses filtered `overview.distinct_projects`; Avg Msgs / Session divides selected message totals by selected session totals. Percentage deltas use the selected current and previous values; a zero previous value displays "New" rather than infinity.
- Aggregate chart series by summing aligned per-harness arrays. Compare uses one dataset per selected harness. Write/read remains blended in both modes. First-prompt Aggregate uses `sum(avg_msgs * n) / sum(n)` per bucket; Compare displays per-harness averages.
- Show every model returned by m1. Give horizontal categorical charts a label-count-derived canvas height inside a bounded scroll region rather than silently dropping or grouping models.
- Replace wrapped "Your Type" with `top_tool.name` and `top_tool.calls`. Wrapped remains unchanged by selection or mode.
- Format date-only values with `Intl.DateTimeFormat` using a short local date. Format session timestamps with local date and time while preserving the exact ISO value in a `title` attribute. Render absent values as an em dash.
- Follow the mock's 1200px centered layout, four KPI cards, paired chart grid, neutral tokens, indigo accent, positional harness colors, gradient wrapped banner, and `prefers-color-scheme` dark mode. Collapse KPI and chart grids progressively, with the paired chart grid becoming one column at 800px.
- Target WCAG 2.2 AA fundamentals: visible focus, native keyboard interactions, sufficient text/background contrast, labels in addition to color, semantic headings/table headers, a live status region, and canvas `role="img"` labels plus concise fallback summaries. Chart.js documents that canvas accessibility must be supplied by the application: https://www.chartjs.org/docs/latest/general/accessibility.html.
- Place each responsive canvas in its own relatively positioned container, as required by Chart.js: https://www.chartjs.org/docs/latest/configuration/responsive.html. Destroy existing chart instances before rebuilding after state changes.
