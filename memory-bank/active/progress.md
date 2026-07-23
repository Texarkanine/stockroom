# Progress

Surface session token usage on the stockroom dashboard: Tokens column on conversation lists (dashboard + full list), Model + Tokens on conversation detail, with a shared reusable compact-count/hover-breakdown component. Spec: [issue #83](https://github.com/Texarkanine/stockroom/issues/83).

**Complexity:** Level 2

## 2026-07-22 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Confirmed intent against issue #83; incorporated reusable token-hover component preference
    - Determined Level 2: enhancement within dashboard subsystem over existing warehouse token data
* Decisions made
    - Level 2 (not L3): multiple UI surfaces but one subsystem; no architectural redesign
* Insights
    - Migration `0007` / view `session_token_usage` already provides the four token metrics; work is primarily API surfacing + dashboard UI

## 2026-07-22 - PLAN - COMPLETE

* Work completed
    - Mapped list/detail UI, metrics assembler, and token VIEW; APIs currently omit tokens
    - Produced TDD plan: API → reusable `dashboard-tokens.mjs` → list column → detail meta → docs
* Decisions made
    - Wire `tokens` as `{input, output, cache_creation, cache_read}` or `null` when `token_grain == 'none'`
    - Compact total = sum of the four fields; shared module required before list/detail wiring
    - Detail gains top-level `model` using the same attribution rule as list rows
* Insights
    - Closest existing chrome is `.panel-help`, but issue requires hover not click — reuse visuals only
