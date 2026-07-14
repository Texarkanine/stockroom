# Task: dashboard-sessions-browse

* Task ID: dashboard-sessions-browse
* Complexity: Level 3
* Type: feature

Close the loop on visual conversation exploration per [#49](https://github.com/Texarkanine/stockroom/issues/49): capped glanceable **Sessions** panel on metrics, deep-linkable paginated sessions-list SPA view, browser-Back-only navigation, efficient COUNT/window retrieval.

## Open Questions

- [x] Sessions retrieval API shape → Resolved: `/api/sessions_ends` for panel `{total,newest,oldest}`; enrich `/api/sessions` to `{total,sessions}` with `offset`/`order`/`limit` (`limit=0` = show-all). See `memory-bank/active/creative/creative-sessions-api-shape.md`
- [ ] Per-page control UX on sessions list → In progress

### Per-page control UX on sessions list

**Problem:** The list page replaces Aggregate/Compare with a per-page control that must include a no-pagination / show-all option; exact UX is left to implementer.

**Why ambiguous:** Fixed presets vs typed custom vs computed-from-total (or mix) all satisfy acceptance criteria but differ in chrome density and URL encoding (`per_page=all` vs omit vs sentinel).

**Constraints:** Must live in the Aggregate/Compare slot; must include show-all at bottom of control; tall pages are acceptable; pagination UI top+bottom when paging is active; URL-owned independent of metrics filters; API uses `limit=0` for show-all (creative-sessions-api-shape).

## Status

- [ ] Component analysis complete
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
