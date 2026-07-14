# Project Brief

## User Story

As a human exploring agentic-coding history on the local dashboard, I want a glanceable Sessions panel plus a deep-linkable paginated sessions list so that I can reach any conversation in the current filter range without loading the full set.

## Use-Case(s)

### Glanceable Sessions on metrics

On the main metrics dashboard, within active harness + time-range filters: if total ≤ 20 show all sessions; if total > 20 show 10 newest, an `… N more` row (`N = total − 20`), and 10 oldest. Row click opens the existing reconstruct view.

### Browse all sessions in range

Clicking `… N more` opens a sessions-list SPA view seeded with the metrics page’s current filters. The list page has its own harnesses + time range + per-page control (including show-all), pagination at top and bottom when paging, and independent URL-owned filter state. Row click opens reconstruct. Browser Back is the only back navigation.

### Agent-constructed deep links

Agents construct localhost dashboard URLs for list and reconstruct views; those URLs must work when a human clicks them.

## Requirements

1. Rename the metrics panel to **Sessions**; apply the ≤20 / 10+ellipsis+10 capping rules with correct `N`.
2. Add a deep-linkable sessions-list SPA view (same `view=` query-param pattern as reconstruct from #39).
3. List page: harnesses + time range; Aggregate/Compare replaced by per-page (including no-pagination); same row fields; pagination UI top and bottom when active.
4. List filters are URL-scoped and independent of metrics filters; `… more` copies then-current metrics filters into the list URL.
5. Remove custom “Back to metrics” (or equivalent) from reconstruct; no custom back on the list page.
6. Efficient retrieval: COUNT + bounded ordered queries / new dashboard API endpoints — not fetch-all-then-slice. Read-only `open_current()`, no schema migration.

## Constraints

1. Out of scope: reconstruct content/export changes beyond removing the custom back link.
2. Out of scope: sharing/collaboration features; extra columns or search-within-list beyond harness + time range.
3. Prefer extending the existing `view=` SPA pattern from [#39](https://github.com/Texarkanine/stockroom/issues/39).
4. Per-page control UX is implementer/creative choice as long as acceptance criteria hold.

## Acceptance Criteria

1. Section title is **Sessions**; ≤20 → all rows; >20 → 10 newest + `… N more` + 10 oldest with correct `N`.
2. `… N more` opens a deep-linkable sessions-list view seeded with current metrics filters.
3. List page has harnesses + time range; Aggregate/Compare replaced by per-page (including a no-pagination option); pagination UI top and bottom when paging.
4. List filters are independent of metrics filters (URL-scoped); browser Back restores prior view.
5. Session rows (metrics or list) still open existing reconstruct; reconstruct has no custom "back to metrics".
6. Totals and page windows come from efficient queries / new endpoints — not "load everything then slice".
7. Agent-constructed URLs for list and reconstruct views work when clicked by a human.

## Source

[GitHub issue #49](https://github.com/Texarkanine/stockroom/issues/49)
