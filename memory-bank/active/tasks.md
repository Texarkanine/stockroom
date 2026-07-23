# Task: dashboard-token-usage

* Task ID: dashboard-token-usage
* Complexity: Level 2
* Type: simple enhancement

Surface session token usage on the stockroom dashboard per [issue #83](https://github.com/Texarkanine/stockroom/issues/83): Tokens column on both conversation lists (between Messages and Model), Model + Tokens on conversation detail (drop redundant Session label), with one reusable compact-count / hover-breakdown component. Back the UI from existing warehouse VIEW `session_token_usage` (migration `0007`) — not yet exposed by dashboard APIs.

## Test Plan (TDD)

### Behaviors to Verify

- **List API tokens present (Claude)**: session with message-grain token totals → `/api/sessions` (and `sessions_ends` via shared assembler) includes a `tokens` object with four integer fields (`input`, `output`, `cache_creation`, `cache_read`); zeros stay `0`, not omitted/null
- **List API tokens absent (Cursor / none)**: session with `token_grain = 'none'` → `tokens` is `null`
- **Detail API tokens + model**: `/api/session` returns top-level `model` (same attribution rule as list) and `tokens` with the same null/zero semantics
- **Compact format**: `formatTokenCompact(n)` maps e.g. `1234→1.2K`, `1_500_000→1.5M` (cursor-style truncated big-counter); `0→0`
- **Compact total from breakdown**: when `tokens` is non-null, display total is sum of the four fields; when `tokens` is null, display is emdash
- **List column placement**: Tokens header sits between Messages and Model on both `#recent-sessions` and sessions-list tables; empty/loading `colspan` is 7
- **Shared mount — data present**: reusable mount renders compact total + hover affordance; hover shows labeled breakdown of all four metrics (zeros shown as `0`)
- **Shared mount — data absent**: reusable mount renders emdash only; no hover affordance / no popover
- **Detail meta line**: `renderSessionDetail` shows `Model` and `Tokens` (via shared mount); does not show `Session:` label
- **Regression**: existing session list/detail fields (`started`, `harness`, `msgs`, `prompt`, messages/tools) unchanged aside from additive `tokens` / detail `model`

### Test Infrastructure

- Framework: pytest (+ xdist) for Python; Node 22 built-in test runner for dashboard JS (`make test-dashboard-js` / `make test-dashboard-py`)
- Test location: `skills/sr-search/tests/` (`test_dashboard_*.py`); `skills/sr-search/tests-js/` (`dashboard-*.test.mjs`)
- Conventions: Python files `test_dashboard_<area>.py`; JS pure-logic tests without DOM where possible; HTML shell contracts in `test_dashboard_static.py`
- New test files: `skills/sr-search/tests-js/dashboard-tokens.test.mjs`
- Extended files: `test_dashboard_metrics.py`, `test_dashboard_static.py`, `dashboard-session.test.mjs`

## Implementation Plan

1. [x] **API helper + list `tokens` field** — `_tokens_payload` + `session_token_usage` join in `_fetch_ordered_sessions` / `_assemble_session_rows`
2. [x] **Detail `tokens` + session-level `model`** — `session_detail` join + plurality model rule
3. [x] **Reusable token UI module** — `dashboard-tokens.mjs` + CSS + tests
4. [x] **List tables: Tokens column** — HTML headers, colspan 7, `appendSessionDataRow` mount
5. [x] **Detail meta: Model + Tokens; drop Session** — `buildSessionMetaEntries` + `renderSessionDetail`
6. [x] **Docs** — `docs/user-guide/dashboard.md`
7. [x] **Verify** — `make test-dashboard-py`, `make test-dashboard-js`, `make lint`, `make format-check`, `make test` (672 passed / 4 skipped; 101 JS)

## Technology Validation

No new technology - validation not required.

## Dependencies

- Warehouse schema ≥ migration `0007` (`session_token_usage`)
- Claude ingest writes message token columns; Cursor leaves them null

## Challenges & Mitigations

- Message join multiplies token columns → set once per session key in assembler
- Hover (not click `.panel-help`) for breakdown
- Detail lacked session-level `model` → same plurality/fallback as list

## Pre-Mortem

- Wrong grain → use VIEW `*_tokens_total` + `token_grain` only
- Duplicated hover markup → shared `mountTokenDisplay`
- colspan regressions → static tests
- Zero as missing → API/mount tests pin `0`

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
