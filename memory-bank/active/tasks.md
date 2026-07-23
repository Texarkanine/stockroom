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

1. **API: attach `tokens` on session list rows**
   - Files: `skills/sr-search/src/stockroom/dashboard/metrics.py`, `skills/sr-search/tests/test_dashboard_metrics.py`
   - Changes: Extend `_fetch_ordered_sessions` SQL with `LEFT JOIN session_token_usage` on `(harness, session_id)`; thread `input/output/cache_creation/cache_read` totals (+ grain) into `_assemble_session_rows`; set `tokens` to `{input, output, cache_creation, cache_read}` when grain ≠ `'none'`, else `null`. TDD: extend `test_sessions_are_recent_filtered_and_display_truncated` (and/or focused new cases) with Claude fixture rows that populate message tokens and Cursor rows that stay null.

2. **API: attach `tokens` + session-level `model` on detail**
   - Files: `skills/sr-search/src/stockroom/dashboard/metrics.py`, `skills/sr-search/tests/test_dashboard_metrics.py`
   - Changes: In `session_detail`, select `sessions.models` and join/query `session_token_usage`; compute top-level `model` with the same plurality/fallback rule as `_assemble_session_rows`; add `tokens` with identical shape/null rules. TDD: extend `test_session_detail_reconstructs_ordered_messages_and_nested_tools`.

3. **Reusable token UI module (pure + mount helpers)**
   - Files: new `skills/sr-search/src/stockroom/dashboard/static/dashboard-tokens.mjs`, `skills/sr-search/tests-js/dashboard-tokens.test.mjs`, wire export from static surface as needed
   - Changes: `formatTokenCompact(n)`, `tokenTotal(tokens)`, `hasTokenData(tokens)`, and `mountTokenDisplay(container, tokens)` (or equivalent) that creates compact text + hover popover markup only when data exists; emdash + no hover when null. Style via small CSS classes in `index.html` (borrow positioning/box cues from `.panel-help`, but hover-triggered). Export from the module for both list and detail.

4. **List tables: Tokens column**
   - Files: `skills/sr-search/src/stockroom/dashboard/static/index.html`, `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, `skills/sr-search/tests/test_dashboard_static.py`
   - Changes: Insert `<th>Tokens</th>` between Messages and Model on both tables; bump all session-table `colSpan`/`colspan` 6→7; in `appendSessionDataRow`, insert shared mount between msgs and model cells. TDD: static HTML assertions for column order + colspan.

5. **Detail meta: Model + Tokens; drop Session**
   - Files: `skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs`, `skills/sr-search/tests-js/dashboard-session.test.mjs` (and/or extract a small pure meta-builder if needed for testability)
   - Changes: In `renderSessionDetail`, replace Session bit with Model (emdash if unknown) and Tokens via shared mount; keep Harness · Project · Started · (Subagent of). Title already shows session id.

6. **Docs**
   - Files: `docs/user-guide/dashboard.md`
   - Changes: Document Tokens column on session lists and Model/Tokens on session inspection (null → emdash; Claude zeros preserved).

7. **Verify**
   - Run targeted dashboard Python + JS tests, then full `make test` (or project-equivalent) before declaring build done.

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
- [ ] Preflight
- [ ] Build
- [ ] QA
