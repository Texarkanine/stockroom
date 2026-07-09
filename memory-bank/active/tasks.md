# Task: p4-dashboard / m2 — Vendored single-pane front-end

* Task ID: p4-dashboard-m2
* Complexity: Level 3
* Type: Feature

Replace the m1 dashboard placeholder with a fully offline, single-pane, accessible dashboard that renders the eight shipped API contracts through a vendored Chart.js 4.5.1 UMD bundle. The browser discovers arbitrary harnesses from API data, owns selection and Aggregate/Compare presentation, preserves m1 metric semantics, and never introduces a write, migration, network, or build path.

## Pinned Info

### Client Data and Rendering Flow

This diagram is the plan's backbone because it fixes the ownership boundaries: m1 remains mode-agnostic, pure transformations are unit-tested outside the DOM, the adapter owns browser state and atomic refresh, and wrapped bypasses selection.

```mermaid
graph TD
    classDef existing fill:#e1f5fe,stroke:#01579b;
    classDef new fill:#f3e5f5,stroke:#7b1fa2;
    classDef thirdParty fill:#fff3e0,stroke:#ef6c00;

    API["m1 JSON endpoints"]:::existing --> Data["dashboard-data.mjs tested coordinator"]:::new
    Data --> Snapshot["Successful immutable snapshot"]:::new
    Snapshot --> Core["dashboard-core.mjs pure transforms"]:::new
    State["Selected harnesses and mode"]:::new --> Data
    State --> Core
    Core --> Cards["KPI and wrapped values"]:::new
    Core --> Datasets["Aggregate or Compare datasets"]:::new
    Datasets --> Adapter["DOM and chart adapter"]:::new
    Chart["Vendored Chart.js 4.5.1 UMD"]:::thirdParty --> Adapter
    Data --> Adapter
    Adapter --> Page["Single-pane semantic dashboard"]:::new
    Snapshot --> Table["Recent sessions table"]:::new
    Table --> Page
    Cards --> Page
    Wrapped["Wrapped fetched unfiltered"]:::existing --> Snapshot
```

## Component Analysis

### Affected Components

- **Static page shell** — `skills/sr-search/src/stockroom/dashboard/static/index.html` currently carries one placeholder line → becomes semantic page structure, inline design tokens/layout CSS, native harness disclosure, Aggregate/Compare radio group, status/error surfaces, KPI cards, chart containers, recent-sessions table, and wrapped banner.
- **Pure client domain logic** — new `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs` → owns deterministic harness ordering/color assignment, selected-series aggregation, weighted averages, KPI/delta/wrapped derivation, generic labels, chart heights, and mode-specific dataset construction without DOM or Chart.js access.
- **Testable data coordinator** — new `skills/sr-search/src/stockroom/dashboard/static/dashboard-data.mjs` → owns request-plan construction, injectable parallel fetch, typed actionable API errors, atomic snapshot completion, and generation/abort gating without DOM or Chart.js access.
- **Browser adapter** — new `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs` → remains a thin effects layer that wires already-tested state transitions, coordinator behavior, and panel models to native controls, safe DOM updates, Chart.js lifecycle, loading/error/empty presentation, local date formatting, and responsive redraw.
- **Vendored chart runtime** — new `skills/sr-search/src/stockroom/dashboard/static/chart-4.5.1.umd.min.js` → verbatim official npm distribution, loaded locally before the browser module and retaining MIT identity.
- **HTTP/static boundary** — `skills/sr-search/src/stockroom/dashboard/server.py` already serves arbitrary files beneath the guarded static root → expected to remain unchanged unless cross-platform `.mjs` MIME testing proves an explicit mapping is required.
- **JavaScript test infrastructure** — new `skills/sr-search/tests-js/dashboard-core.test.mjs` and `dashboard-data.test.mjs`, plus `Makefile` and `.github/workflows/ci.yml` → Node 22 built-in test runner becomes part of local/full CI without npm, a package manifest, or a build step.
- **Python static and HTTP contracts** — new `skills/sr-search/tests/test_dashboard_static.py` and extensions to `tests/test_dashboard_server.py` → verify semantic asset wiring, offline-only references, packaged serving, MIME types, and traversal behavior without pretending to prove browser rendering.
- **Licensing** — `REUSE.toml`, new `LICENSES/MIT.txt`, and `skills/sr-search/tests/test_licensing.py` → authored HTML/ES modules and `tests-js/**` resolve to AGPL while the exact Chart.js artifact resolves to MIT.
- **Technical context** — `memory-bank/techContext.md` → records Node 22 as a contributor test prerequisite, native ES modules/no-build ownership, the pinned Chart.js artifact, and the static asset/test locations.

### Cross-Module Dependencies

- `index.html` → local `chart-4.5.1.umd.min.js` → global `Chart`; then `index.html` → `dashboard.mjs` as a native module.
- `dashboard.mjs` → `dashboard-core.mjs`: all deterministic transformations cross this seam; the DOM adapter does not duplicate metric math.
- `dashboard.mjs` → `dashboard-data.mjs` → `/api/overview|trends|projects|tools|models|efficiency|sessions|wrapped`: the coordinator receives injected `fetch`, seven endpoints receive repeated selected `harness` parameters, and wrapped never does.
- `dashboard.mjs` → Chart.js: adapter creates and destroys chart instances; core returns plain labels/datasets/options inputs.
- `server.py` → `static/`: existing traversal-safe file serving exposes all committed assets without package-data or build configuration.
- `tests-js/dashboard-core.test.mjs` / `dashboard-data.test.mjs` → corresponding static modules via `../src/stockroom/dashboard/static/*.mjs`: native ESM imports under Node 22, with no browser or third-party dependency.
- pytest → static files/loopback server/REUSE CLI: verifies artifact and licensing boundaries; browser MCP/manual QA verifies actual rendered behavior.

### Boundary Changes

- **New public static routes:** `/dashboard.mjs`, `/dashboard-core.mjs`, `/dashboard-data.mjs`, and `/chart-4.5.1.umd.min.js` become loopback-served assets. No JSON endpoint shape, warehouse schema, CLI, or Python API changes.
- **Contributor toolchain:** the full test gate gains Node 22 and `node --test`; runtime users still need only the existing locked Python environment and a browser.
- **Licensing contract:** dashboard-authored `.html`/`.mjs` files are explicitly AGPL despite the surrounding `skills/**` PPL-S layer; only the pinned Chart.js file is MIT.

### Invariants and Constraints

- Every dashboard database request remains read-only through `warehouse.open_current()`; m2 adds no database, migration, ingest, or write path.
- Runtime is fully offline: no CDN, external font, analytics, dynamic import URL, or fetch target outside same-origin `/api/*`.
- Harness keys are discovered from data, sorted deterministically, and mapped positionally to the fixed eight-color palette; more than eight harnesses cycle the palette without blocking discovery.
- Aggregate/Compare remains client-owned; KPI meanings do not change by mode; Projects uses filtered `overview.distinct_projects`; First-Prompt Aggregate is weighted by `n`; Write/Read remains blended.
- Wrapped remains all-time and unfiltered. Its eighth factual field is Top Tool, not a derived personality.
- The page remains single-pane with no drill-down, conversation reconstruction, token/cost, subagent, or branch UI.
- Warehouse-derived strings enter the document through `textContent`/attributes, never raw HTML.
- Tests follow the mandated stub tests → stub interfaces → implement tests and observe failure → implement behavior sequence; browser-only visual checks stay in the sanctioned manual QA boundary.
- `make ci`, including pytest, Node tests, Ruff, lock verification, and REUSE, is green at the milestone boundary.

## Open Questions

- [x] Interaction and presentation contract → Resolved: contract-first native dashboard with atomic refresh, accessible native controls, endpoint-owned windows, truthful m1 fields, global actionable errors, and Top Tool replacing "Your Type" (see `memory-bank/active/creative/creative-dashboard-interaction-contract.md`).
- [x] Test-first strategy for client logic → Resolved: pure native ES module under Node 22's built-in test runner; pytest for static/HTTP/licensing contracts; browser rendering in manual QA (see `memory-bank/active/creative/creative-dashboard-js-testing.md`).

## Test Plan

### Behaviors to Verify

#### Automated JavaScript Unit Behaviors

- Arbitrary unsorted harness keys → sorted unique harness list and stable positional colors; the ninth harness cycles without being dropped.
- Raw harness keys containing hyphens/underscores → generic title-cased display labels without a curated harness map.
- Selected harness names containing spaces/reserved characters → URL builder emits repeated encoded `harness` parameters; sessions includes `limit=50`; wrapped omits filters.
- Aligned per-harness arrays with selected, missing, and zero-only harnesses → element-wise aggregate of selected data with no input mutation.
- Aggregate mode → one summed dataset; Compare mode → one labeled/colorized dataset per selected harness in deterministic order.
- Weekly writes/reads in either mode → two blended selected-harness series, never per-harness Compare series.
- First-prompt `avg_msgs` plus `n` → weighted bucket averages; zero total observations produce zero rather than `NaN`.
- Filtered overview payload → Sessions and Messages sums, Projects from `distinct_projects`, and Avg Msgs / Session with a zero-session guard.
- Current/previous values → signed rounded percentage; previous zero/current positive → `New`; both zero → neutral no-change label.
- Label count → deterministic minimum/dynamic chart height that keeps all model rows available.
- Null/invalid display values → em dash or zero-safe outputs rather than exceptions.
- Input payloads passed through every pure transform → remain unchanged.
- Overview harness discovery → deterministic all-selected initial state; toggling the final selected harness is rejected; mode transitions report no refetch while selection transitions report refetch.
- Selected harness set → eight-request plan with repeated encoded filters on seven endpoints, `limit=50` on sessions, and an unfiltered wrapped URL.
- Injected fetch where all eight responses succeed → one complete named snapshot; any non-OK response rejects atomically with sanitized `error` and optional `action`, without exposing a partial snapshot.
- Overlapping coordinator generations → only the latest token can commit; superseded work is aborted/ignored.
- Daily payload → Aggregate vertical bar with one summed session dataset; Compare vertical stacked bars with one dataset per selected harness.
- Projects payload → Aggregate horizontal bar with summed counts; Compare horizontal stacked bars.
- Tools payload → Aggregate doughnut of summed calls; Compare horizontal stacked bars.
- Weekly payload → two blended selected-harness line datasets for writes and reads in both modes.
- Efficiency payload → Aggregate vertical bar with summed buckets; Compare vertical stacked bars.
- Models payload → Aggregate horizontal bar with summed sessions; Compare horizontal stacked bars, preserving every model.
- First-prompt payload → Aggregate vertical bar with weighted averages; Compare grouped, non-stacked bars per harness.
- Wrapped payload with populated or nullable fields → exactly eight ordered factual cell models, with span as the Total Sessions subtitle and zero/em-dash fallbacks.

#### Automated Python Static and Boundary Behaviors

- Packaged root request → complete HTML document with `stockroom dashboard`, semantic landmark, labeled native controls, live status/error regions, required panel IDs, semantic recent-sessions table, and canvas fallback labels.
- HTML script/style/resource references → local relative assets only; no `http://`, `https://`, protocol-relative URL, CDN host, external font, or inline remote fetch target.
- Requests for authored `.mjs` assets and pinned Chart.js → 200 with JavaScript MIME and non-empty bodies; encoded traversal remains rejected.
- Script load order → pinned Chart.js UMD precedes the module adapter; adapter imports both authored core/data modules, which are not separate `index.html` script tags.
- REUSE SPDX map → `index.html`, `dashboard.mjs`, and `dashboard-core.mjs` resolve only to AGPL-3.0-or-later.
- REUSE SPDX map → `chart-4.5.1.umd.min.js` resolves to MIT and not AGPL/PPL-S; `reuse lint` remains clean with canonical `LICENSES/MIT.txt`.
- REUSE SPDX map → `dashboard-data.mjs` and both `skills/sr-search/tests-js/*.test.mjs` files resolve only to AGPL-3.0-or-later.

#### Manual Browser and Integration Behaviors

- Current populated warehouse → one initial same-origin request per endpoint, all panels render real values, and no external network request occurs.
- Initial 503 missing/stale/busy response → visible `error` plus `action`; a later successful refresh clears it.
- Selection change → seven filterable endpoints refetch with repeated harness filters, wrapped remains unchanged, and the last selected harness cannot be removed.
- Mode change → no network fetch; KPI/table/wrapped meanings stay fixed while relevant charts switch summed/doughnut versus stacked/grouped datasets.
- Rapid selection changes → stale responses cannot overwrite the newest selection; prior successful data remains visible during refresh/failure.
- Empty/zero payloads and nullable wrapped fields → stable zero cards, chart no-data summaries, empty table row, and em dashes without console exceptions.
- Light/dark system themes and widths above/below 800px → readable contrast, one-column collapse, no clipped labels, and all-model chart remains scrollable.
- Keyboard-only flow → disclosure, checkboxes, radio group, focus order, focus visibility, and closing behavior remain usable; color is never the only harness cue.
- Chart canvases → concise accessible labels/fallback summaries; recent sessions retain semantic column headers.
- Session and wrapped dates → local short formatting with exact session ISO timestamps preserved in `title`.

### Test Infrastructure

- Frameworks: pytest 8 for Python/static/licensing boundaries; Node 22 stable built-in `node:test` + `node:assert/strict` for browser-domain and data-coordinator logic.
- Python test location: `skills/sr-search/tests/`; JavaScript test location: `skills/sr-search/tests-js/`.
- Conventions: descriptive `test_*` Python functions with behavior docstrings; `.test.mjs` files using explicit native imports; no npm/package.json/transpilation; whole-suite execution through root `make test` and `make ci`.
- New test files: `skills/sr-search/tests/test_dashboard_static.py`, `skills/sr-search/tests-js/dashboard-core.test.mjs`, `skills/sr-search/tests-js/dashboard-data.test.mjs`.
- Extended test files: `skills/sr-search/tests/test_dashboard_server.py`, `skills/sr-search/tests/test_licensing.py`.

### Integration Tests

- Extend the loopback server test to request the real packaged HTML, all three authored modules, and pinned Chart.js, verifying MIME and guarded serving as one boundary.
- Preserve the existing fixture ingest → real warehouse → `open_current()` → HTTP overview test; m2 consumes that frozen API contract and needs no duplicate DB integration test.
- Use browser automation/manual QA against the real foreground server and populated local warehouse for end-to-end fetch/render/offline verification; do not add a flaky browser suite to CI.

## Chart and Wrapped Mapping

| Panel | Aggregate | Compare |
|---|---|---|
| Daily Activity | Vertical bar, one summed sessions dataset | Vertical stacked bars, one dataset per harness |
| Sessions by Project | Horizontal bar, summed counts | Horizontal stacked bars |
| Tool Distribution | Doughnut, summed calls | Horizontal stacked bars |
| Write/Read Ratio | Two blended line datasets | Same two blended line datasets |
| Session Efficiency | Vertical bar, summed buckets | Vertical stacked bars |
| Model Distribution | Horizontal bar, all models summed | Horizontal stacked bars, all models |
| First-Prompt Quality | Vertical bar, weighted averages | Grouped non-stacked bars per harness |

The wrapped banner has exactly eight cells: Total Sessions with `totals.span` as its subtitle, Total Messages, Distinct Projects, Busiest Harness, Best Streak, Marathon Session, Peak Hour, and Top Tool. `overview.last_sync` appears in the header rather than a KPI or wrapped cell.

## Interface Inventory

- `dashboard-core.mjs`: `sortedHarnesses`, `displayHarness`, `harnessColors`, `transitionViewState`, `sumAligned`, `weightedSeries`, `deriveOverviewCards`, `buildWrappedPanel`, `formatDelta`, `chartHeight`, and one explicit panel-model builder for each row in the chart matrix: `buildDailyPanel`, `buildProjectsPanel`, `buildToolsPanel`, `buildWriteReadPanel`, `buildEfficiencyPanel`, `buildModelsPanel`, `buildFirstPromptPanel`.
- `dashboard-data.mjs`: `buildRequestPlan`, `DashboardRequestError`, `fetchSnapshot(fetchImpl, selectedHarnesses, options)`, and `createRequestGate`.
- `tests-js/*.test.mjs` imports modules through `../src/stockroom/dashboard/static/<module>.mjs`; no package manifest or resolver configuration is required.

## Implementation Plan

1. [x] **Prepare every test, interface, and runner without implementing behavior.**
    - Files: `skills/sr-search/tests-js/dashboard-core.test.mjs`, `skills/sr-search/tests-js/dashboard-data.test.mjs`, `skills/sr-search/tests/test_dashboard_static.py`, `skills/sr-search/tests/test_dashboard_server.py`, `skills/sr-search/tests/test_licensing.py`, `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard-data.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, `Makefile`, `.github/workflows/ci.yml`.
    - Test stubs first: add every planned Node/pytest test with an empty implementation and explanatory comments where the signature is not self-describing; modify existing test modules only after stubs exist.
    - Interface stubs second: add every documented export from the Interface Inventory with empty implementations, plus a browser adapter entry that performs no fetch, transition, transformation, or rendering.
    - Runner wiring: add `NODE ?= node`, a `.PHONY` `test-js` target that explicitly refuses missing/non-22 Node and runs `cd $(ENGINE) && $(NODE) --test tests-js/*.test.mjs`, make `test: sync test-js`, and let `ci` inherit it through `test`. In GitHub CI, add `actions/setup-node@v4` pinned to Node 22 and a separate `node --test tests-js/*.test.mjs` step under the existing engine working directory.
    - Do not replace the placeholder page, vendor Chart.js, add licensing rules, or implement any transformation in this step.
    - Creative ref: `creative-dashboard-js-testing.md`.
2. [x] **Implement and fail all pure client contract tests, then build the core module behavior by behavior.**
    - Files: `skills/sr-search/tests-js/dashboard-core.test.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs`.
    - Fill tests for harness ordering/colors/labels, non-empty selection and mode/selection transition effects, array aggregation, weighted averages, KPI/delta semantics, the exact wrapped cell map/null guards, dynamic heights, immutability, and every explicit chart-matrix panel builder.
    - Run the Node test file and confirm the newly implemented tests fail against the stubs.
    - Implement one pure export at a time, rerunning the focused Node suite after each behavior; refactor shared selected-series traversal only after green.
3. [x] **Implement and fail the data-coordinator contracts, then build fetch orchestration behavior by behavior.**
    - Files: `skills/sr-search/tests-js/dashboard-data.test.mjs`, `skills/sr-search/src/stockroom/dashboard/static/dashboard-data.mjs`.
    - Fill tests for the eight-URL request plan, repeated filters, sessions limit, wrapped omission, injected parallel fetch, atomic success/failure, sanitized actionable errors, abort forwarding, and latest-generation commit gating.
    - Run the focused Node test and confirm failure against the Step 1 stubs.
    - Implement one coordinator export at a time and rerun after each behavior. No fetch/generation/error policy may be added later in `dashboard.mjs`.
4. [x] **Lock vendored-asset, static-page, MIME, and license contracts before adding assets or page behavior.**
    - Files: `skills/sr-search/tests/test_dashboard_static.py`, `skills/sr-search/tests/test_dashboard_server.py`, `skills/sr-search/tests/test_licensing.py`.
    - Fill the prepared pytest cases for semantic landmarks/panel IDs, local-only resource references, script ordering, served `.mjs`/Chart.js MIME, AGPL authored assets/data coordinator/tests-js, and MIT Chart.js. Extend the existing static-root test rather than replacing its traversal assertion.
    - Run these focused pytest modules and `reuse lint`; confirm failures due to the placeholder, absent assets, and missing MIT annotation/license.
    - If the real `.mjs` request does not produce a JavaScript MIME on a supported platform, add a narrow explicit `.mjs` registration in `server.py` only after the failing server test, then rerun it; accept either standard JavaScript MIME spelling in the assertion.
5. [x] **Vendor Chart.js and establish precise REUSE ownership.**
    - Files: `skills/sr-search/src/stockroom/dashboard/static/chart-4.5.1.umd.min.js`, `LICENSES/MIT.txt`, `REUSE.toml`.
    - Extract `dist/chart.umd.min.js` verbatim from the official `chart.js@4.5.1` npm tarball already validated in planning; use the versioned filename as the runtime pin.
    - Add canonical MIT text and ordered REUSE overrides: the exact authored `index.html`, `dashboard.mjs`, `dashboard-core.mjs`, `dashboard-data.mjs`, and `skills/sr-search/tests-js/**` paths to AGPL, then the exact Chart.js file to `MIT` with the upstream package copyright.
    - Rerun focused licensing tests and `reuse lint`; do not modify the minified upstream artifact to satisfy formatting or headers.
6. [x] **Build the semantic responsive page shell and pass static contracts.**
    - Files: `skills/sr-search/src/stockroom/dashboard/static/index.html`.
    - Replace the placeholder with the header/control region, status/error live region, four KPI cards, seven chart panels, recent-sessions table, and eight-cell wrapped banner.
    - Add inline authored CSS for the mock-guided tokens, 1200px layout, cards, chart containers, responsive breakpoints, dark scheme, visible focus, screen-reader utilities, and no-data states.
    - Load the local versioned UMD bundle before `dashboard.mjs`; include labels/fallback summaries for every canvas.
    - Rerun `test_dashboard_static.py` and server asset tests until green.
    - Creative ref: `creative-dashboard-interaction-contract.md`.
7. [x] **Wire the thin browser adapter to already-green state and data contracts.**
    - Files: `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, `skills/sr-search/src/stockroom/dashboard/static/index.html`.
    - Use the tested core transition helpers to discover/default harnesses, render a native disclosure/checklist and Aggregate/Compare radio group, prevent an empty selection, and distinguish mode-only redraw from selection refetch.
    - Use only the tested coordinator to fetch eight endpoints, filter seven, retain the previous snapshot while busy, suppress stale generations, and commit complete snapshots.
    - Surface sanitized global errors/actions through text nodes; distinguish initial loading, refreshing, refusal, and legitimate no-data states.
    - Keep warehouse-derived strings out of `innerHTML`. This step may contain only DOM/Chart.js effects; if any deterministic policy is discovered, return to Step 2 or 3, add/fail its test, and implement it there before wiring.
8. [x] **Render all measured content through already-green panel models.**
    - Files: `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`.
    - Render header `last_sync`, truthful KPIs/deltas and proportional harness bars; consume the seven tested panel builders exactly as specified in the chart matrix; rebuild through a centralized chart registry.
    - Render all recent sessions with generic harness labels/colors and exact ISO titles; consume the tested `buildWrappedPanel` result unfiltered.
    - No new pure export or metric math is permitted in this step. If a gap appears, return to Step 2's failing-test loop before changing the adapter.
9. [x] **Complete cross-browser accessibility, responsive, and offline QA.**
    - Files: `skills/sr-search/src/stockroom/dashboard/static/index.html`, `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`.
    - Verify keyboard flow, visible focus, semantic table/controls, live announcements, canvas labels/fallbacks, color-plus-text encoding, light/dark contrast, 800px collapse, and dynamic all-model scrolling.
    - Run the real server against populated data, inspect all panels in Aggregate and Compare, exercise one/many harnesses, resize/theme changes, and each 503 action.
    - Disable external network or inspect requests to prove every runtime asset/API request remains loopback-only. Fix stockroom code found by the smoke pass; do not add tests for Chart.js/browser internals.
10. [x] **Document and run the complete milestone gate.**
    - Files: `memory-bank/techContext.md`.
    - Record Node 22, the no-package native module test command, static asset locations, Chart.js 4.5.1 vendoring, and manual browser QA boundary.
    - Run formatting/linting, focused Node and pytest suites, `make reuse`, then the entire `make ci` gate. Because `make ci` exact-syncs, restore the documented per-machine Torch build afterward and rerun the production encoder smoke as the established milestone-boundary check.
    - Finish with a real foreground dashboard smoke and confirm no untracked vendoring/build debris.

## Technology Validation

- **Chart.js 4.5.1:** `npm view` confirmed the current package version and MIT license. A temporary extraction of the official npm tarball confirmed `dist/chart.umd.js` exposes `globalThis.Chart.version === "4.5.1"` with no install or build. Runtime artifact will be the minified UMD file served locally. Official responsive-container guidance: https://www.chartjs.org/docs/latest/configuration/responsive.html; accessibility boundary: https://www.chartjs.org/docs/latest/general/accessibility.html.
- **Node 22 built-in test runner:** local Node 22.22.1 is available; `node:test` is stable since Node 20 and requires no package. CI will pin major 22 explicitly. Official runner documentation: https://nodejs.org/docs/latest-v22.x/api/test.html.
- **No package/build addition:** no npm dependency, `package.json`, JavaScript lockfile, bundler, transpiler, or runtime network fetch is introduced.

## Challenges & Mitigations

- **REUSE override order can silently apply PPL-S to browser code/tests or AGPL to Chart.js:** lock exact resolved licenses for authored static files, the data coordinator, and `tests-js/**` in `test_licensing.py`; place their AGPL overrides before the exact-file MIT override and after broad `skills/**`.
- **Vendored bytes can drift from the pinned release:** obtain the artifact only from the official `chart.js@4.5.1` npm tarball, preserve it verbatim, use a versioned filename, and review it as an upstream binary/minified asset rather than formatted project code.
- **`.mjs` MIME inference varies by platform:** test the real server and accept standard JavaScript MIME spellings; add a narrow explicit mapping immediately after a demonstrated failing test, not as untested prophylaxis.
- **Rapid filter changes can race:** use `AbortController` where available plus a monotonically increasing generation token; render only the newest complete snapshot.
- **Per-harness arrays may be missing, empty, or differently sparse:** centralize aligned selected-series traversal in the pure core, zero-fill by labels, and test missing/zero cases.
- **Project and average math are easy to make visually plausible but semantically wrong:** use filtered `distinct_projects` and weighted `avg_msgs * n` in tested core functions; never recompute them ad hoc in chart code.
- **Many models can overflow a fixed chart:** derive chart height from label count and place it in a bounded scroll region; never silently trim or group.
- **Canvas is not inherently accessible:** provide meaningful canvas labels/fallback summaries and keep exact values available in semantic text/table surfaces where practical, following Chart.js guidance.
- **Node becomes a new contributor prerequisite:** pin Node 22 in CI, make the missing-command failure explicit in `make test-js`, document it in `techContext.md`, and avoid npm so the new surface remains minimal.
- **Full CI exact sync removes the per-machine Torch exception:** follow the documented restoration and production encoder smoke procedure after `make ci`; this is known tooling debt, not m2 functionality.
- **Browser testing can sprawl into low-ROI platform proofs:** automate only stockroom-owned deterministic logic and asset contracts; keep Chart.js rendering, CSS, and native browser behavior in the explicit manual QA checklist.

## Preflight Findings

- **PASS after in-phase amendments:** convention, dependency, conflict, completeness, security, offline, accessibility, and public-boundary checks found no architectural or scope blocker.
- **TDD hardening:** extracted injectable request orchestration into tested `dashboard-data.mjs`; added exact core/data interface inventory; bound state transitions, stale-generation gating, actionable failures, all seven panel models, and the wrapped map to explicit failing-test loops before adapter wiring.
- **Licensing hardening:** added exact planned AGPL coverage and assertions for every authored static module and `tests-js/**`, followed by an exact-file MIT override for Chart.js.
- **Completeness hardening:** added the chart/mode matrix, exact eight-cell wrapped map, `last_sync` placement, all-three-module serving/import contracts, explicit Makefile/CI Node wiring, and reactive `.mjs` MIME handling.
- **Radical innovation incorporated:** the testable data coordinator is an accretive in-scope improvement that keeps the browser adapter effects-only without adding a framework or package dependency.
- **Advisories:** none remain that warrant plan changes before build.

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [ ] QA

## QA Results

- **Result:** FAIL
- **Trivial fixes applied during QA:**
  - Restored the dashboard-spec positional palette (`#6366f1`, `#10b981`, `#f59e0b`, `#f43f5e`, `#06b6d4`, `#8b5cf6`, `#ec4899`, `#84cc16`).
  - Treated nullable `peak_hour.hour` as an em dash instead of `00:00`.
  - Localized wrapped span/streak date subtitles with short local dates.
  - Raised wrapped-banner secondary text contrast above WCAG 4.5:1.
  - Updated `README.md` for Phase 4 status and the Node 22/`make test-js` gate.
- **Substantive blockers remaining:**
  1. **Projects KPI delta is semantically wrong.** `deriveOverviewCards` compares filtered `distinct_projects` against the sum of per-harness `prev_projects`. Shared projects are double-counted on the previous side, so an unchanged shared project can show `-50%`. The m1 overview payload has no previous-window distinct count, and m2 forbade JSON shape changes, so the fix needs a plan decision: add `prev_distinct_projects`, hide the Projects delta, or otherwise redefine the card.
  2. **Chart canvases lack meaningful accessible summaries.** `renderChart` and the static canvas fallbacks expose only the chart title/mode, not values or a concise data summary. The interaction contract and manual QA checklist require canvas labels plus fallback summaries that convey measured content.
- **Validation after trivial fixes:** 25/25 Node contracts and 18/18 focused static/HTTP/licensing contracts pass.
