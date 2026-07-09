# Current Task: p4-dashboard / m2 — Vendored single-pane front-end

**Complexity:** Level 3

## Open Questions

- [x] What complete interaction and presentation contract should m2 adopt where the design guides are silent or conflict with the shipped m1 API? → Resolved: use a contract-first native dashboard with atomic refresh, native accessible controls, endpoint-owned windows, filtered distinct Projects, all-model scrolling, global actionable errors, and Top Tool replacing unsupported "Your Type" (see `memory-bank/active/creative/creative-dashboard-interaction-contract.md`).
    - Ambiguity: viable choices remain for projects in Compare mode, the wrapped banner's unsupported "Your Type" slot, error/loading/empty states, date and harness-name formatting, explicit versus endpoint-default windows, model overflow, keyboard accessibility, and responsive behavior.
    - Constraints: m1 payload semantics win over guide examples; the UI stays single-pane, fully offline, open to arbitrary harness names, client-owned for Aggregate/Compare, accessible without color alone, and small enough to remain a no-build vanilla HTML/JS surface.
- [x] How should m2 test client-owned JavaScript behavior test-first without adding a build pipeline or a flaky browser suite? → Resolved: isolate pure behavior in a native ES module and test it with Node 22's built-in `node:test`; keep DOM/Chart.js rendering as manual QA and retain pytest for HTTP/static/licensing contracts (see `memory-bank/active/creative/creative-dashboard-js-testing.md`).
    - Ambiguity: static pytest assertions cannot verify transformations, Node's built-in test runner would introduce a new developer prerequisite, and a headless-browser dependency is disproportionate; relying only on manual smoke conflicts with the workspace's strict TDD rule for deterministic logic.
    - Constraints: tests must exercise stockroom-owned logic, `make ci` must remain the complete gate, runtime stays fully offline with Chart.js as the only front-end dependency, committed layout remains the install layout, and browser rendering itself should remain manual QA under the milestone's test-ROI exception.
