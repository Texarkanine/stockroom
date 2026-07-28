---
task_id: dashboard-marathon-link-and-msg-deep-link-investigate
date: 2026-07-27
complexity_level: 2
---

# Reflection: dashboard-marathon-link-and-msg-deep-link-investigate

## Summary

Wrapped Marathon Session now deep-links to that conversation, and session bubbles expose `#msg-N` ordinal anchors with post-render top-of-bubble scroll. Delivered as planned after operator chose full scope.

## Requirements vs Outcome

All requirements met: marathon link uses existing session deep-link shape; ordinal investigation concluded feasible and was implemented with `#msg-{ordinal}` and `scrollIntoView({ block: "start" })`. Docs updated. No descopes.

## Plan Accuracy

Plan was accurate: API already had `session_id` in SQL but omitted it from JSON; URL assembly stayed in `dashboard.mjs`. Main surprise was operational — `make lint`'s frozen sync stripped local torch mid-verification.

## Build & QA Observations

TDD cycles were straightforward. QA only needed a trivial invalid-ordinal guard (`messageAnchorId` → null) so bubbles never get `msg-NaN`.

## Insights

### Technical
- Dashboard "link" UX should keep a real `href` (middle-click/new-tab) and SPA-navigate on plain click — session list rows are click-only and are a weaker pattern for shareable destinations.
- `make sync` / `make lint` still strip out-of-lock torch; prefer `uv run --no-sync ruff` when the embedding stack must stay installed, and heal from `{stockroom_home}/torch-requirements.txt`.

### Process
- Investigation-first scope with an explicit operator gate ("both" vs "marathon only") kept ordinal work from either stalling or shipping unapproved UI.

### Million-Dollar Question

Nothing notable — session query deep-links plus message hashes is the natural shape; we would still keep URL assembly out of `dashboard-core` and scroll after async detail render.
