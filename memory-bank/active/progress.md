# Progress

Add per-conversation skill and tool-call distribution visualizations (pie charts, pending layout pick) on the dashboard conversation overview, plus an advanced query recipe; layout chosen via internet prior art + mockups and operator visual UAT ([issue #107](https://github.com/Texarkanine/stockroom/issues/107)).

**Complexity:** Level 3

## 2026-07-29 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Intent clarified: pie charts + query recipe; internet prior art + mockups for visual layout pick
    - Classified as Level 3
* Decisions made
    - Level 3 (not L2): open placement design needing creative/mockups + operator pick; spans dashboard UI, data surface, and docs
* Insights
    - L2 plan has no creative loop; L3 creative (low-confidence stop) matches "show me mockups and I'll pick"

## 2026-07-29 - CREATIVE (session-distribution-placement) - COMPLETE (unresolved)

* Work completed
    - Component analysis for #107 (session pane, Chart.js doughnuts, session_detail gaps, cookbook)
    - Internet prior art: header usage stats (PocketDev, AgentsView); transcript+sidebar (Helvia)
    - HTML mockups A/B/C/D with dashboard design tokens
* Decisions made
    - Low confidence — operator must visually pick placement
    - Non-binding recommendation: D header dials (else B inline)
* Insights
    - Metrics pane already owns doughnut language; session view has no side rail today
    - Skills need session-scoped derivation; tools can aggregate from nested tool_calls or SQL
