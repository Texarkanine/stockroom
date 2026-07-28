# Project Brief

## User Story

As a dashboard user, I want the Wrapped "Marathon Session" cell to open that conversation, and I want to know whether message bubbles can deep-link by ordinal via URL hash (anchored to the top of the bubble), so I can jump straight to a specific turn.

## Use-Case(s)

### Open marathon conversation

From the Wrapped panel, click the Marathon Session value (or cell) and land on that session's conversation reconstruction view.

### Investigate message ordinal deep-links

Assess whether bubbles in conversation reconstruction can expose ordinal indicators that deep-link via URL hash to that message, scrolling so the top of the bubble is at the viewport top. Report feasibility and recommended approach; implement only if straightforward after scope agreement.

## Requirements

1. Marathon Session in Wrapped is a link to that session's existing conversation deep-link.
2. Investigate message-ordinal hash deep-linking for convo reconstruction bubbles (anchor to top of bubble).
3. Prefer existing session-view URL conventions; do not invent a parallel navigation system for marathon alone.

## Constraints

1. Stay within the dashboard UI/static JS and existing session deep-link machinery unless investigation proves a backend gap.
2. Message-ordinal work is investigation-first; full implementation is out of scope until feasibility and approach are confirmed.

## Acceptance Criteria

1. Clicking Marathon Session navigates to that conversation (same experience as other session deep-links).
2. Investigation produces a clear yes/no on ordinal hash deep-links, with recommended hash shape, scroll behavior (top of bubble), and any blockers (e.g. missing ordinals in render path).
3. Tests cover the marathon link behavior; ordinal deep-link work is tested only if implemented in this task.
