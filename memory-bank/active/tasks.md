# Task: dashboard-model-analytics

* Task ID: dashboard-model-analytics
* Complexity: Level 3
* Type: feature

Ship [#67](https://github.com/Texarkanine/stockroom/issues/67) (top models by conversation and by message) and [#68](https://github.com/Texarkanine/stockroom/issues/68) (stacked area model usage over time) on the existing offline dashboard.

## Pinned Info

### Dual-grain data flow

Shared attribution feeds ranked bars and time-series areas so grains never disagree.

```mermaid
flowchart TD
  WH[(sessions + messages)] --> Attr["Attribution helper<br/>conv set ∪ msg sole-model fallback"]
  Attr --> Rank["models()<br/>by_conversation + by_message"]
  Attr --> Trends["model_trends()<br/>bucketed stacks"]
  Rank --> API1["/api/models"]
  Trends --> API2["/api/model_trends"]
  API1 --> Bars["Two half-width bars"]
  API2 --> Areas["Two panel-wide stacked areas"]
```

## Component Analysis

### Affected Components
- **`stockroom.dashboard.metrics`**: Session-grain `models()` + trend bucketing helpers. → Shared attribution; dual-grain `models()` payload; new `model_trends()`.
- **`ENDPOINTS` / server**: Registers metric handlers. → Add `model_trends`; keep `models` key with new shape.
- **`dashboard-data.mjs`**: Fetch plan list. → Include `model_trends`.
- **`dashboard-core.mjs`**: `buildModelsPanel`. → Conversation + message bar builders; stacked-area builders; shared model→color helper.
- **`dashboard.mjs`**: Chart.js render + wiring. → New panel names; `fill`/stack options for area; wire snapshot fields.
- **`index.html`**: Single `models-panel`. → Two bar panels + two `panel-wide` area panels; update canvas count / order pins.
- **Tests**: metrics, static, server, JS core/data. → Behaviors below.
- **Docs (light)**: `docs/user-guide/dashboard.md` if it enumerates panels — add brief mention of dual-grain model charts if/when that page lists them (currently sparse; only update if a panel inventory exists or screenshot captions need refresh).

### Cross-Module Dependencies
- Client `ENDPOINTS` list ↔ server `metrics.ENDPOINTS` keys.
- Attribution helper ↔ both metric functions.
- Model color map ↔ all four model panels.

### Boundary Changes
- `/api/models` JSON shape becomes dual-grain (clean break; dashboard is sole consumer).
- New `/api/model_trends`.
- Static panel inventory grows (+3 panels net: −1 old models, +2 bars, +2 areas).
- No schema/ingest changes.

### Invariants & Constraints
- Offline read-only `open_current()`.
- Harness-honest attribution (see creative).
- Aggregate/Compare: bars keep harness stacks; areas filter harnesses server-side and stack **models only**.
- TDD; existing Make targets.

## Open Questions

- [x] **Dual-grain model attribution** → Resolved: sole-session-model fallback for assistant turns; conversation grain keeps union once-per-session (`memory-bank/active/creative/creative-dual-grain-attribution.md`)
- [x] **Top-models presentation (#67)** → Resolved: two half-width bars with grain in titles (`creative-top-models-presentation.md`)
- [x] **Model-over-time presentation (#68)** → Resolved: two `panel-wide` stacked areas; Compare filters harnesses into model stacks (`creative-model-over-time-presentation.md`)

## Test Plan (TDD)

### Behaviors to Verify

**Attribution / metrics (Python)**
- Conversation grain: session with model only in `sessions.models` counts once for that model.
- Conversation grain: session with model only on a message counts once.
- Conversation grain: same model on session list + messages still counts once.
- Conversation grain: subagent sessions excluded.
- Message grain: Claude assistant turn with `messages.model=M` increments M.
- Message grain: Cursor assistant turn with NULL model and sole `sessions.models=[M]` increments M.
- Message grain: Cursor assistant turn with NULL model and multi-model `sessions.models` increments nothing.
- Message grain: user turns never increment (even with sole session model).
- Message grain: rankings independent of conversation rankings (high message / low session model can outrank).
- `model_trends` conversation: session activity buckets increment the session’s models once per session per bucket.
- `model_trends` message: attributed assistant turns bucket by message `ts` (fallback session activity if needed).
- `model_trends`: adaptive granularity via `_trend_granularity` for bounded windows; default window aligns with models (30d).
- Empty warehouse / empty window → empty model lists / zero-filled or empty series consistent with other metrics.
- Harness filter: only selected harnesses contribute.

**API / static**
- `ENDPOINTS` includes `models` and `model_trends`.
- `/api/models` returns `by_conversation` + `by_message` shapes.
- `/api/model_trends` returns `labels`, `granularity`, `by_conversation`, `by_message`.
- HTML: panels `models-conversation-panel`, `models-message-panel`, `model-trends-conversation-panel`, `model-trends-message-panel` (exact ids pinned in tests).
- Two bar panels half-width; two trend panels have `panel-wide`.
- Canvas count / order pins updated (models pair before efficiency; wide trends after models pair).
- Request plan includes `model_trends`.

**JS panel builders**
- `buildModelsConversationPanel` / `buildModelsMessagePanel` (names as implemented): aggregate vs compare harness stacks; empty → empty flag.
- Stacked-area builders: `kind: "line"`, `fill: true`, `stacked: true`, one dataset per model, colors stable for a given model id across builders.
- Compare mode on area builders does not invent harness datasets (model stacks only).

### Test Infrastructure

- Framework: pytest (+ xdist) under `skills/sr-search/tests/`; Node 22 `--test` under `skills/sr-search/tests-js/`.
- Conventions: `test_<behavior>` in `test_dashboard_metrics.py` / `test_dashboard_static.py`; JS `node:test` in `dashboard-core.test.mjs` / `dashboard-data.test.mjs`.
- New test files: none required (extend existing). Optional small `test_model_attribution.py` only if helper grows large enough to warrant isolation — default keep in `test_dashboard_metrics.py`.

### Integration Tests

- Server smoke already hits every `ENDPOINTS` key — registering `model_trends` covers HTTP 200.
- Static inventory + adapter import/wiring pins cover HTML↔`dashboard.mjs` coupling.

## Implementation Plan

1. **Attribution helper + dual-grain `models()` (TDD)**
    - Files: `metrics.py`, `tests/test_dashboard_metrics.py`
    - Changes: extract helper; rewrite `models()` to return `{ by_conversation: { models, sessions }, by_message: { models, messages } }` (harness→aligned arrays). Creative: dual-grain attribution.
2. **`model_trends()` (TDD)**
    - Files: `metrics.py`, `tests/test_dashboard_metrics.py`
    - Changes: new function; `ENDPOINTS["model_trends"] = model_trends`; payload `{ labels, granularity, by_conversation: { models, counts }, by_message: { models, counts } }` with model→int[] already summed for selected harnesses. Reuse `_trend_granularity` / `_bucket_labels` / `_activity_bucket`. Creative: over-time presentation.
3. **Client fetch plan**
    - Files: `dashboard-data.mjs`, `tests-js/dashboard-data.test.mjs`
    - Changes: add `model_trends` to `ENDPOINTS` list.
4. **Panel builders + model colors (TDD)**
    - Files: `dashboard-core.mjs`, `tests-js/dashboard-core.test.mjs`
    - Changes: split/replace `buildModelsPanel`; add area builders; `colorForModel(model, palette)` stable across panels. Creative: both UI docs.
5. **Static HTML inventory**
    - Files: `index.html`, `tests/test_dashboard_static.py`
    - Changes: two bar panels + two `panel-wide` area panels; titles with grain; update canvas count and order assertions.
6. **Wire render path**
    - Files: `dashboard.mjs`
    - Changes: import builders; map snapshot; Chart.js options honor `fill` for line/area; register new chart names in refresh path.
7. **Docs touch (if needed)**
    - Files: `docs/user-guide/dashboard.md` and/or screenshot captions only if panel list or hero screenshot is explicitly outdated — skip if page stays high-level.
8. **Verify**
    - `make test-dashboard-py` and `make test-dashboard-js`, then full `make test` before declaring build done.

## Technology Validation

No new technology — validation not required. Stacked area uses existing vendored Chart.js 4.5.1 (`line` + `fill` + stacked scales).

## Challenges & Mitigations

- **Breaking `/api/models` shape**: Sole consumer is dashboard; update JS + tests in same change set; server endpoint loop covers new key.
- **Cursor multi-model silence on message grain**: By design (creative); conversation charts still show those sessions; don’t “fix” with fan-out.
- **Color consistency across four panels**: Shared `colorForModel` from ranked union or stable hash into `PALETTE`.
- **Area chart render options**: Extend `chartOptions` / dataset mapping for `fill` without breaking Write/Read (`fill: false`).
- **Static test canvas count**: Update explicitly when panels change (currently asserts `len(canvases) == 8` → expect 11).
- **Independent ranking vs shared Y labels**: Bars rank per grain independently (creative); areas use each grain’s model set for the window.

## Pre-Mortem

- **Plan failed because message grain looked “broken” for Cursor users**: Already covered by Challenge (honesty) — mitigate in UI with clear titles, not fake data; optional one-line empty copy if message panel empty while conversation has data.
- **Plan failed because stacked areas were unreadable with dozens of models**: Add a follow-up step only if needed: cap to top-N models by total + “other” bucket — **out of initial scope** (YAGNI); note as post-ship if clutter appears.
- **Plan failed because Compare mode users expected harness-colored areas**: Creative explicitly rejected harness×model stacks; document in panel behavior — if operators push back, that’s a rework, not a silent change mid-build.
- **Plan failed by treating attribution as chart-local**: Prevented by pinned helper + single creative; implementation step 1 lands helper before UI.

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
