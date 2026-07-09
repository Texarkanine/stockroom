# Decision: Dashboard JavaScript Testing

## Context

M2 places deterministic selection, aggregation, weighted-average, formatting, and chart-dataset logic in the browser. The decision is how to exercise that stockroom-owned logic test-first when the repository currently has pytest but no JavaScript runner. Static source assertions cannot prove transformations, while browser rendering tests would add a large dependency and violate the milestone's test-ROI discipline. The solution must keep `make ci` complete, preserve the no-build committed-layout contract, add no dashboard runtime dependency beyond vendored Chart.js, and leave inherently visual rendering to manual QA.

## Options Evaluated

- **Node built-in unit tests over ES modules**: Isolate pure client transformations in a native `.mjs` module and test them with stable `node:test` and `node:assert/strict`, with Node pinned only in CI and required for contributors.
- **Pytest static contracts plus manual browser QA**: Assert asset references, forbidden external URLs, and semantic markers in Python, then verify every dynamic behavior manually.
- **Headless browser automation**: Add Playwright or an equivalent browser dependency and exercise the complete page in CI.
- **Move aggregation into Python**: Shift client transformations into the tested backend and make the browser a thin renderer.

## Analysis

| Criterion | Node built-in unit tests | Static contracts + manual QA | Headless browser automation | Move logic into Python |
|---|---|---|---|---|
| Strict TDD for deterministic logic | Direct and fast | Fails to exercise behavior | Direct but slow and broad | Direct, but tests the wrong boundary |
| Runtime dependency impact | None | None | None at runtime, large dev payload | None |
| Developer tooling impact | Adds Node 22 prerequisite, no npm packages | None | Adds Node, browser binaries, and package management | None |
| Architectural fit | Preserves client-owned Aggregate/Compare | Preserves boundary but weakens verification | Preserves boundary | Violates the mode-agnostic API/client-ownership contract |
| CI reliability | Deterministic, no DOM or network | Deterministic but incomplete | Browser and timing variability | Deterministic |
| Scope | Small Makefile/CI addition plus module split | Smallest immediate diff | Disproportionate new test stack | Crosses completed m1 backend scope |

Key insights:

- The no-build constraint does not require one monolithic inline script. Native browser modules are committed assets and need no transpilation, package manifest, or installation step.
- `node:test` is stable and built into Node, so deterministic logic can be tested without introducing npm, a JavaScript lockfile, or third-party test packages. Official documentation: https://nodejs.org/docs/latest-v22.x/api/test.html.
- Browser behavior divides cleanly: pure transformations are stable unit-test targets; Chart.js rendering, CSS layout, and native control interaction are the flaky-by-nature portion covered by the milestone's manual-QA exception.
- Making Node explicit is preferable to silently relying on whatever version happens to exist on hosted runners.

## Decision

**Selected**: Node built-in unit tests over ES modules

**Rationale**: This is the only option that satisfies strict TDD for stockroom-owned deterministic client logic without changing the m1 API boundary or importing a browser automation stack. Native `.mjs` files preserve the no-build and offline contracts, and Node's stable built-ins need no npm dependency or lockfile.

**Tradeoff**: Contributors running the full test gate need Node 22 in addition to uv/Python. The UI is split across a pure core module and a DOM adapter instead of living entirely inline in `index.html`.

## Implementation Notes

- Add `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs` with pure exports for harness ordering/colors, repeated query parameters, aligned-series aggregation, weighted averages, KPI/delta derivation, display labels, and chart dataset construction where it is independent of the DOM.
- Add `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs` as the browser adapter: fetch lifecycle, DOM updates, Chart.js instance registry, native control events, and responsive rendering. It imports the core module; `index.html` loads the vendored Chart.js UMD first and then the browser module with `type="module"`.
- Add `skills/sr-search/tests-js/dashboard-core.test.mjs` using only `node:test` and `node:assert/strict`. Follow the workspace TDD order: stub tests, stub exported interfaces, implement tests and observe failures, then implement one behavior at a time.
- Add a root `test-js` Make target and include it in `test`/`ci`. Pin Node 22 in `.github/workflows/ci.yml` with the official setup action, then run `node --test tests-js/*.test.mjs` from the engine directory. Record Node 22 as a contributor test prerequisite in `techContext.md`.
- Keep pytest coverage for HTTP-served local assets, no external URLs, semantic/static page contract, and REUSE license resolution. Do not use source-text assertions as substitutes for client behavior tests.
- Keep actual Chart.js canvas rendering, responsive layout, color-scheme appearance, focus flow, and offline-network verification in the QA manual smoke pass; these are the sanctioned browser-dependent checks.
