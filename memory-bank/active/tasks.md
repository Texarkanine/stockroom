# Current Task: p4-dashboard / m2 — Vendored single-pane front-end

**Complexity:** Level 3

## Open Questions

- [x] What complete interaction and presentation contract should m2 adopt where the design guides are silent or conflict with the shipped m1 API? → Resolved: use a contract-first native dashboard with atomic refresh, native accessible controls, endpoint-owned windows, filtered distinct Projects, all-model scrolling, global actionable errors, and Top Tool replacing unsupported "Your Type" (see `memory-bank/active/creative/creative-dashboard-interaction-contract.md`).
    - Ambiguity: viable choices remain for projects in Compare mode, the wrapped banner's unsupported "Your Type" slot, error/loading/empty states, date and harness-name formatting, explicit versus endpoint-default windows, model overflow, keyboard accessibility, and responsive behavior.
    - Constraints: m1 payload semantics win over guide examples; the UI stays single-pane, fully offline, open to arbitrary harness names, client-owned for Aggregate/Compare, accessible without color alone, and small enough to remain a no-build vanilla HTML/JS surface.
