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
- New test files: `skills/sr-search/tests-js/dashboard-tokens.test.mjs` (formatter + mount contract helpers)
- Extended files: `test_dashboard_metrics.py`, `test_dashboard_static.py`; optionally `test_dashboard_server.py` if HTTP envelope assertions need the new fields

## Implementation Plan

Each numbered step is one TDD cycle: write/extend the failing test first, run it red, implement only enough to pass, re-run green, then refactor if needed.

1. **API helper + list `tokens` field**
   - Files: `skills/sr-search/tests/test_dashboard_metrics.py`, `skills/sr-search/src/stockroom/dashboard/metrics.py`
   - Test first: Add focused cases (and update exact-equality expectations in `test_sessions_are_recent_filtered_and_display_truncated` + `test_sessions_ends_row_fields_match_sessions_list_shape`) so Claude sessions with message token columns yield `tokens: {input, output, cache_creation, cache_read}` (zeros kept as `0`) and Cursor/`none` yield `tokens: null`.
   - Then implement: Add `_tokens_payload(grain, input, output, cache_creation, cache_read) -> dict | None` in `metrics.py`; extend `_fetch_ordered_sessions` with `LEFT JOIN session_token_usage`; fold totals into `_assemble_session_rows` via the helper (set once per session key despite message-row multiplication).

2. **Detail `tokens` + session-level `model`**
   - Files: `skills/sr-search/tests/test_dashboard_metrics.py`, `skills/sr-search/src/stockroom/dashboard/metrics.py`
   - Test first: Extend `test_session_detail_reconstructs_ordered_messages_and_nested_tools` (Cursor → `tokens: null`, `model: "gpt-5"`) and add a Claude detail case with zeros/non-zeros proving shared payload shape.
   - Then implement: In `session_detail`, select `sessions.models`, query/join `session_token_usage`, compute top-level `model` with the same plurality/fallback rule as list rows, attach `tokens` via `_tokens_payload`.

3. **Reusable token UI module**
   - Files: `skills/sr-search/tests-js/dashboard-tokens.test.mjs` (new), `skills/sr-search/src/stockroom/dashboard/static/dashboard-tokens.mjs` (new), CSS in `index.html`
   - Test first: Pure tests for `formatTokenCompact`, `tokenTotal`, `hasTokenData`, and DOM-free helpers that describe mount decisions (emdash vs compact+hover). Pin compact strings (`0`, `999`, `1.2K`, `1.5M`).
   - Then implement: Export those helpers plus `mountTokenDisplay(container, tokens)` (compact total + hover breakdown only when data exists). Hover-triggered popover; reuse `.panel-help` visual cues only (not click-toggle). Style with new classes in `index.html`.

4. **List tables: Tokens column**
   - Files: `skills/sr-search/tests/test_dashboard_static.py`, `skills/sr-search/src/stockroom/dashboard/static/index.html`, `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
   - Test first: Assert both session tables have header order `… Messages, Tokens, Model, First prompt …` and loading/empty `colspan`/`colSpan` = 7.
   - Then implement: Insert Tokens `<th>`; bump colspan 6→7 (including “N more” / empty rows in `dashboard.mjs`); import `mountTokenDisplay` into `appendSessionDataRow` between msgs and model.

5. **Detail meta: Model + Tokens; drop Session**
   - Files: `skills/sr-search/tests-js/dashboard-session.test.mjs` (and/or extract a small pure meta-builder into `dashboard-session.mjs` / `dashboard-tokens.mjs` if DOM-bound code is hard to assert), `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`
   - Test first: Assert meta builder includes Model + Tokens and omits Session label.
   - Then implement: Update `renderSessionDetail` meta bits; mount Tokens via shared component; keep Harness · Project · Started · (Subagent of).

6. **Docs**
   - Files: `docs/user-guide/dashboard.md`
   - Changes: Document Tokens column on session lists and Model/Tokens on session inspection (null → emdash; Claude zeros preserved). Docs follow code once Steps 1–5 are green.

7. **Verify**
   - Run `make test-dashboard-py` and `make test-dashboard-js`, then full `make test` before declaring build done.

## Preflight Amendments

- Explicit per-step test-before-code ordering (TDD encoding was insufficient in the first draft).
- Shared Python `_tokens_payload` for list + detail (avoids duplicated grain/null rules).
- Exact-equality tests `test_sessions_are_recent_filtered_and_display_truncated` and `test_sessions_ends_row_fields_match_sessions_list_shape` must gain `tokens` expectations (dependency impact).

## Technology Validation

No new technology - validation not required. Reuses DuckDB VIEW `session_token_usage`, existing dashboard ES modules, and native CSS hover / existing popover visual language.

## Dependencies

- Warehouse schema ≥ migration `0007` (`session_token_usage`) — already on main
- Claude ingest already writes message token columns; Cursor leaves them null
- Dashboard opens warehouse via `open_current()` (read-only, no migrate) — VIEW must already exist on the operator's DB (normal after ingest/migrate path)

## Challenges & Mitigations

- **Message join multiplies token columns**: `_fetch_ordered_sessions` LEFT JOINs messages, so token fields repeat per message row — mitigate by setting `tokens` once per session key in `_assemble_session_rows` (setdefault / first-write-wins).
- **Hover vs existing click `.panel-help`**: Issue requires hover breakdown — do not reuse click-toggle panel-help behavior; reuse visual chrome only.
- **Detail lacked session-level `model`**: List already computes it; detail must add the same rule so UI can show Model without scanning messages client-side.
- **Compact formatting edge cases** (exact 1000, rounding): pin expected strings in `dashboard-tokens.test.mjs` and match cursor-style truncation (1 decimal when truncated).
- **Stale local warehouse without 0007**: dashboard `open_current()` will fail or lack the VIEW — out of scope for this UI task; operator remedy remains ingest/migrate via normal stockroom paths. Document only if an existing troubleshooting note needs a pointer.

## Pre-Mortem

- **Wrong grain / summing native+message**: If UI summed both grains or used from_messages when native exists, Claude/Cursor semantics break — plan uses VIEW `*_tokens_total` + `token_grain` only (already covered by Challenge on assembler join).
- **Duplicated hover markup drifts**: Without a shared module, list vs detail diverge — Step 3 makes the reusable component a hard prerequisite before Steps 4–5.
- **colspan / column-order regressions**: Empty-state rows and “N more” rows forget colspan 7 — static tests in Step 4 lock both tables and empty cells.
- **Treating zero as missing**: Showing emdash for Claude zeros contradicts the issue — API and mount tests explicitly require `0` to render as zero.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
