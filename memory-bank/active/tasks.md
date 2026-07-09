# Task: p4-dashboard / m2 — Vendored single-pane front-end (QA rework)

* Task ID: p4-dashboard-m2
* Complexity: Level 3
* Type: Feature (plan rework after QA FAIL)

Close the two substantive QA blockers against the otherwise-complete m2 dashboard: make the Projects KPI delta semantically truthful, and supply content-bearing accessible summaries for every chart canvas. Preserve the shipped offline single-pane surface, m1 mode-agnostic endpoints, and Node/pytest contracts already green.

## Open Questions

- [ ] **Projects KPI previous-window contract** — Current Projects uses filtered `overview.distinct_projects`, but the delta compares that distinct count to the sum of per-harness `prev_projects`. Shared projects are double-counted on the previous side, so an unchanged shared project can show a false decline. Ambiguous because three viable fixes exist: add `prev_distinct_projects` to the overview JSON, hide the Projects delta, or redefine the card to a summable metric. Constraints: KPI meanings stay mode-independent; Projects must remain a distinct count for the selected set; inventing a previous distinct client-side is impossible without previous-window project ids; additive API changes must stay read-only and keep existing fields.
- Chart accessible summaries are **not** an open question: `creative-dashboard-interaction-contract.md` already requires canvas `role="img"` labels plus concise fallback summaries that convey measured content. Title/mode-only labels are incomplete implementation against that settled contract.

## Status

- [ ] Component analysis complete
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
