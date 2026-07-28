---
task_id: dashboard-marathon-link-and-msg-deep-link-investigate
complexity_level: 2
date: 2026-07-28
status: completed
---

# TASK ARCHIVE: Dashboard Marathon Link & Message Ordinal Deep-Links

## SUMMARY

The Wrapped "Marathon Session" cell is now a deep-link that opens that session's conversation reconstruction, and every message bubble in reconstruction exposes an ordinal indicator (`#N`) that deep-links via URL hash (`#msg-{ordinal}`) with post-render scroll anchoring the top of the bubble to the viewport top. The ordinal work began as an investigation; it was judged feasible, the operator approved full scope ("both"), and it shipped in the same Level 2 build.

## REQUIREMENTS

- Marathon Session in Wrapped links to that session's conversation using the existing session deep-link conventions (no parallel navigation system).
- Investigate message-ordinal hash deep-linking for reconstruction bubbles, anchored to the top of the bubble; implement only if straightforward after scope agreement.
- Tests cover the marathon link behavior and (since implemented) the ordinal deep-link behavior.
- Stay within the dashboard UI/static JS and existing session deep-link machinery unless investigation proved a backend gap.

## IMPLEMENTATION

Investigation verdict: feasible. The `session_detail` API already returned per-message `ordinal`; the gap was purely client render/navigation. The one backend gap found was that the Wrapped `marathon_session` JSON omitted `session_id` even though the SQL already selected it.

TDD steps, each one cycle:

1. API: include marathon `session_id` in the Wrapped JSON.
2. Pure cell model: expose `sessionLink` identity fields (harness/sessionId) from `dashboard-core.mjs` without URL shapes.
3. DOM: marathon cell rendered as a real `<a href="?view=session&…">` with SPA `openSessionView` on plain click (progressive enhancement — middle-click/new-tab still work).
4. Pure helpers: `messageAnchorId` / `parseMessageHash` / `resolveMessageAnchorElement` / deep-link ordinal resolution.
5. Ordinal indicators (`#N` linking to `#msg-N`), bubble ids, and `scroll-margin-top`.
6. Hash scroll after async detail load via `scrollIntoView({ block: "start" })`, plus `hashchange` handling; clicking an ordinal uses `preventDefault` + `pushState` and reuses the loaded session detail instead of refetching.
7. User-facing docs in `docs/user-guide/dashboard.md`.

Key design decisions: URL assembly stays in `dashboard.mjs` (out of the import-free `dashboard-core.mjs`); default browser hash scroll is insufficient because messages render after an async fetch, so scrolling happens post-render.

Post-merge review feedback (PR #98) removed a redundant `location.search` `?`-strip before the hash helper.

## TESTING

- Full TDD: tests written first for each step; each cycle run to red then green.
- Final full suite: 113 JS tests + 792 pytest passed (2 skipped); ruff clean.
- `/niko-qa` semantic review passed after one trivial fix: `messageAnchorId` now returns null for non-non-negative-integer ordinals so bubbles never get `msg-NaN` ids.

## LESSONS LEARNED

- Dashboard "link" UX should keep a real `href` (middle-click/new-tab) and SPA-navigate on plain click — the click-only session list rows are a weaker pattern for shareable destinations.
- `make sync` / `make lint` strip the out-of-lock torch install; prefer `uv run --no-sync ruff` when the embedding stack must stay installed, and heal from `{stockroom_home}/torch-requirements.txt`.
- Ordinal hash clicks initially reloaded the conversation; the fix was `preventDefault` + hash `pushState` plus reusing the already-loaded session detail on popstate.

## PROCESS IMPROVEMENTS

- Investigation-first scope with an explicit operator gate ("both" vs "marathon only") kept the ordinal work from either stalling the task or shipping unapproved UI. Worth repeating for enhancement-plus-investigation bundles.

## TECHNICAL IMPROVEMENTS

- Session list rows could adopt the same real-`<a>` + SPA-click pattern as the marathon cell for shareable, middle-clickable navigation.

## NEXT STEPS

None.
