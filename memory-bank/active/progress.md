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

## 2026-07-22 - PREFLIGHT - COMPLETE

* Work completed
    - Validated TDD encoding, conventions, dependency impact, completeness against codebase
    - Amended plan with per-step test-first wording, `_tokens_payload`, and exact-equality test updates
    - Wrote `.preflight-status` = PASS
* Decisions made
    - Keep hover (not click) for token breakdown; shared JS module + shared Python payload helper
* Insights
    - Additive `tokens` field will break two exact session-dict assertions until tests are updated first

## 2026-07-22 - BUILD - COMPLETE

* Work completed
    - API: `_tokens_payload` + list/detail join to `session_token_usage`; detail session-level `model`
    - UI: `dashboard-tokens.mjs` shared mount; Tokens column; detail meta via `buildSessionMetaEntries`
    - Docs + full verification (`make test` 672 passed / 4 skipped; 101 JS)
* Decisions made
    - Labeled detail mount shows `Tokens: —` (no hover) when data absent
    - Compact total = sum of four fields; breakdown labels Input / Output / Cache write / Cache read
* Insights
    - Message-join token columns are safe when set once on session setdefault
