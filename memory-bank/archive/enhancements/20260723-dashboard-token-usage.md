---
task_id: dashboard-token-usage
complexity_level: 2
date: 2026-07-23
status: completed
---

# TASK ARCHIVE: dashboard-token-usage

## SUMMARY

Surfaced session token usage on the stockroom dashboard per [#83](https://github.com/Texarkanine/stockroom/issues/83) / [PR #89](https://github.com/Texarkanine/stockroom/pull/89): Tokens column on both conversation lists (between Messages and Model), Model + Tokens on conversation detail (dropped redundant Session label), via one reusable compact-count / hover-breakdown mount. Backed by existing warehouse VIEW `session_token_usage` (migration `0007`) newly joined in dashboard APIs. Post-build polish added Total row + alignment tweaks and addressed PR review on tokens guard/tests.

## REQUIREMENTS

1. Tokens column on dashboard recent list and full sessions list, between Messages and Model.
2. Compact K/M count with hover breakdown when token data exists; em dash with no hover when `token_grain == 'none'` (e.g. Cursor).
3. Claude: four metrics; zeros render as `0`, not em dash.
4. Detail: Model + Tokens at top; remove Session label; same token semantics.
5. Shared reusable component for compact display + hover breakdown across list and detail.

**Constraints:** Prefer existing `session_token_usage`; match dashboard em-dash null conventions.

**Acceptance:** All met (column placement, hover-only-when-present, detail meta, shared mount, zero vs missing).

## IMPLEMENTATION

1. API: `_tokens_payload` + `session_token_usage` join in list assembler and session detail; `tokens` is `{input, output, cache_creation, cache_read}` or `null`; detail also gets session-level `model` (same plurality rule as list).
2. UI: `dashboard-tokens.mjs` (`formatTokenCompact`, `mountTokenDisplay`); Tokens column + colspan 7; detail meta via `buildSessionMetaEntries`.
3. Docs: `docs/user-guide/dashboard.md` (+ screenshot refresh).
4. `techContext.md`: lists `dashboard-tokens.mjs` and session `tokens` API exposure.

| Area | Files |
|------|--------|
| API | `skills/sr-search/src/stockroom/dashboard/metrics.py` |
| UI | `dashboard-tokens.mjs`, `dashboard-session.mjs`, `dashboard.mjs`, `index.html` |
| Tests | `test_dashboard_metrics.py`, `test_dashboard_static.py`, `dashboard-tokens.test.mjs`, `dashboard-session.test.mjs` |
| Docs | `docs/user-guide/dashboard.md`, dashboard screenshot assets |

## TESTING

- TDD: list/detail API tokens present vs null; compact format; shared mount present/absent; column placement / colspan; detail meta; regression on existing fields.
- Verify: `make test-dashboard-py`, `make test-dashboard-js`, `make lint`, `make format-check`, `make test` — **672 passed / 4 skipped**; **101 JS**.
- `/niko-preflight` PASS; `/niko-qa` PASS (one trivial DRY fix: single `tokenBreakdownRows` pass in `mountTokenDisplay`).

## LESSONS LEARNED

### Technical

- Dashboard session list enrichment multiplies rows via LEFT JOIN messages; session-level fields (tokens) must be set once on setdefault, not per message row.

### Process

- Nothing notable for this task.

### Million-dollar question

If tokens had been a first-class dashboard assumption from day one, list/detail would have shared the same `tokens` payload shape and mount from the start — which is essentially what shipped. No deeper redesign warranted.

## PROCESS IMPROVEMENTS

None — plan sequence (API → shared module → list → detail → docs) held; anticipated challenges were the real ones.

## TECHNICAL IMPROVEMENTS

None beyond what shipped. Labeled vs unlabeled mount covers list and detail without a second component.

## NEXT STEPS

- Land / merge [PR #89](https://github.com/Texarkanine/stockroom/pull/89); close or annotate [#83](https://github.com/Texarkanine/stockroom/issues/83) as delivered.
