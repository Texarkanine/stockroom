---
task_id: p4-dashboard-m2
date: 2026-07-09
complexity_level: 3
---

# Reflection: Vendored single-pane front-end

## Summary

The milestone replaced the dashboard placeholder with the planned fully offline, accessible, single-pane front-end over all eight shipped metric APIs. The implementation, browser integration pass, complete CI gate, and subsequent semantic QA all succeeded.

## Requirements vs Outcome

Every m2 requirement shipped: open harness discovery, positional colors, client-owned Aggregate/Compare, mode-independent KPIs, seven chart panels, recent sessions, the exact eight factual wrapped cells, atomic same-origin refresh, actionable warehouse refusals, responsive light/dark presentation, vendored Chart.js 4.5.1, precise REUSE ownership, Node 22 contracts, and no package manager or build path.

Nothing was descoped. The only added interface was `deriveHarnessBreakdown`, introduced test-first when the already-planned proportional KPI rendering needed a pure owner. The browser pass also added a live color-scheme redraw listener; this completed the planned theme behavior rather than expanding scope. Migrating the local populated warehouse from v3 to v4 was test-environment recovery through an existing documented action, not a product change.

## Plan Accuracy

The preflight-amended ten-step plan was accurate in sequence, scope, and file ownership. Preparing interfaces and tests before behavior kept the TDD order explicit; separating pure transforms, request coordination, page structure, browser effects, and measured rendering allowed each layer to become green before integration.

The identified high-risk seams were the right ones. REUSE override order required exact rules and tests; request races warranted abort/generation gating; weighted first-prompt and distinct-project semantics needed pure contracts; and browser-only responsive/accessibility/offline checks could not be replaced by source assertions. `.mjs` MIME inference did not fail on the supported environment, so the planned evidence-driven server fallback was correctly unnecessary.

Two integration details were not predicted precisely. The real warehouse was one migration behind, but the m1 actionable 503 contract made recovery immediate. Chart.js canvas colors did not automatically follow a live system-theme change; the browser pass exposed this and a centralized redraw fixed it without architectural change. Level 3 was the right estimate: the task was substantial and cross-cutting, but remained within the established backend and needed no rearchitecture.

## Creative Phase Review

The contract-first native interaction decision held throughout implementation. Native disclosure, checkboxes, radios, semantic table markup, live regions, and one atomic snapshot delivered the required behavior with less state and accessibility risk than custom widgets or panel-independent fetches. Replacing the unsupported personality field with Top Tool kept every wrapped value factual.

The native-ESM/Node-testing decision also held. Pure panel/state math and coordinator policy ran directly under Node 22 without npm, while the adapter remained limited to DOM, localization, and Chart.js effects. The one browser-discovered theme issue confirmed that the selected boundary was honest: deterministic application policy belonged in unit tests, while canvas rendering and live media behavior still required a real browser.

## Build & QA Observations

The staged TDD cycles went smoothly: 18 core contracts and five coordinator contracts failed against stubs before implementation, static/serving/licensing contracts failed for the expected absent artifacts, and each layer then turned green in plan order. Exact REUSE assertions prevented the broad `skills/**` prompt-content rule from silently claiming authored JavaScript or Chart.js.

The populated browser pass was the most valuable integration activity. It verified real request counts and filters, no-refetch mode changes, stale-generation suppression, retained snapshots, empty states, dates, narrow layouts, accessibility semantics, offline-only traffic, and both themes. It found the only product defect, the live canvas-theme redraw gap, before the milestone gate. The later semantic QA found no KISS, DRY, YAGNI, completeness, regression, integrity, documentation, or licensing correction to make.

## Cross-Phase Analysis

Preflight materially improved build quality. Extracting `dashboard-data.mjs` before implementation prevented fetch, error, and generation policy from accumulating in the adapter. Enumerating every chart and wrapped mapping made missing panels or speculative display facts easy to detect. Exact license-path planning prevented a late vendoring cleanup.

The creative decisions reduced rather than created QA risk. Native controls removed custom-widget complexity, and the pure-module boundary made the effects adapter auditable. Planning could not prove Chart.js's response to a live theme change, but it correctly reserved that class of behavior for browser QA, which caught it. Consequently the formal QA phase was clean rather than a rework cycle.

## Insights

### Technical

- Treat a dashboard refresh as one immutable application snapshot when all panels share a warehouse and timestamp boundary; abort plus generation gating preserves coherence without per-panel state machines.
- Canvas libraries own rendered colors after creation. CSS custom-property changes require an explicit redraw path even when the surrounding page updates automatically.
- In layered REUSE repositories, vendored browser software and authored code under prompt-shaped directories need exact resolved-license tests, not only broad annotation rules.
- A no-build front-end can retain strong TDD seams: native modules provide enough structure to test deterministic policy without importing a package manager or browser harness.

### Process

- Define the browser-test boundary by behavior, not convenience: unit-test stockroom-owned deterministic policy, statically test packaging/security contracts, and reserve native interaction, layout, canvas, and media changes for a real-browser pass.
- Preflight interface and ownership inventories paid for themselves on this Level 3 feature; they converted likely integration discoveries into explicit failing-test loops before adapter work.
- The Level 3 estimate was accurate. Ten build checkpoints were verbose but kept the multi-surface TDD progression recoverable, while no additional design cycle or QA rework was needed.
