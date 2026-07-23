# Project Brief

## User Story

As a stockroom user, I want to see token usage on the dashboard conversation lists and conversation detail pages so that I can gauge cost/usage at a glance without leaving the UI.

## Use-Case(s)

### Conversation list token column

On the dashboard recent-conversations list and the full conversation list, show a Tokens column between Messages and Model. Compact count (K/M) with hover breakdown when data exists; emdash with no hover when token fields are unknown (e.g. Cursor).

### Conversation detail model + tokens

On a conversation deep-dive page, show Model (if known) and Tokens at the top. Drop the redundant Session label. Same compact count + hover breakdown semantics; emdash with no hover when no token data.

### Shared token hover UI

Use one reusable component for the token compact display and hover breakdown so list and detail surfaces do not duplicate the popup markup/behavior.

## Requirements

1. Implement as specified in [GitHub issue #83](https://github.com/Texarkanine/stockroom/issues/83).
2. Tokens column on both conversation list surfaces, between Messages and Model.
3. Compact truncated count (K, M, etc.) with hover `?` breakdown matching cursor.com/dashboard semantic (per issue screenshots).
4. Claude Code: show all four metrics; zeros render as zero (not emdash).
5. Cursor / missing fields: emdash (same null/unknown pattern as model); no hover on emdash/empty token data.
6. Conversation detail: Model + Tokens at top; remove Session label to free horizontal space; `Tokens: XXX` is the hover target.
7. Factor token compact display + hover breakdown into a reusable component used by list and detail views.

## Constraints

1. Work in the detached git worktree for this chat; do not modify the primary working tree.
2. Prefer reuse of existing warehouse token data (`session_token_usage` / related session fields) rather than inventing a parallel metrics path.
3. Match existing dashboard null/unknown presentation conventions (emdash).

## Acceptance Criteria

1. Dashboard and full conversation lists show a Tokens column between Messages and Model with correct compact formatting.
2. Hover breakdown appears only when token data is present; emdash rows/fields have no hover.
3. Conversation detail shows Model and Tokens (no Session label) with the same token semantics.
4. Token display/hover is implemented via a shared reusable component, not copy-pasted across the three call sites.
5. Claude Code sessions with zero tokens show `0` (or equivalent zero), not emdash.
