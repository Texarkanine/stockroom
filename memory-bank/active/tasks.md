# Tasks

Task ID: compact-session-composition-empty-state

## compact-session-composition-empty-state

### Build — COMPLETE

- **What broke:** Empty Tools/Skills (and other) chart panels kept a ~280px chart-wrap, so “No tool/skill …” looked like tall blank boxes.
- **Why:** `renderChart` always assigned full wrap height before early-returning on `model.empty`.
- **Fix:** `chartWrapLayoutStyle(empty, height)` collapses wrap to `0px` when empty; `renderChart` applies it. Empty copy still shown.
- **Files:** `dashboard-core.mjs`, `dashboard.mjs`, `tests-js/dashboard-core.test.mjs`
- **Verify:** `make test-dashboard-js` (118), `make test-dashboard-py` (136), `make test` (793 passed, 4 skipped)

### QA — PASS

- Compact empty state meets rework AC; no visitor/query rewrite (correctly out of scope).
- Helper is minimal and reused by all chart panels (including session composition).

### Follow-up (post-QA) — DONE (flushed /nk-save)

- Denser session composition: `withSessionCompositionLayout` (height 176, legend right); main metrics doughnuts unchanged.
- FOUC: session wraps CSS `height: 0` until paint; `resetSessionCompositionCharts` on session load; expand only when data arrives.
- Cut CSS/`176px`/function-name source-string asserts per Texarkanine/.cursor-rules#95; kept executable `chartWrapLayoutStyle` / `withSessionCompositionLayout` unit tests.
