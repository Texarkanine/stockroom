# Project Brief

## User Story

As a dashboard user, I want the token-usage tooltip to float above the conversations panel without causing scrollbars so that I can read token details without the layout shifting or clipping.

## Use-Case(s)

### Use-Case 1

Hover (or focus) the token-usage help control (`?`) in the sessions/conversations view; the tooltip appears outside the scrollable panel and does not introduce a vertical scrollbar on that panel.

### Use-Case 2

When the help control is near the top or bottom of the scroll view, the tooltip remains fully visible (preferred: bleed into surrounding page space; alternative: flip top/bottom alignment based on available space).

## Requirements

1. Fix the bug described in https://github.com/Texarkanine/stockroom/issues/91.
2. Token tooltip must not render clipped inside its panel or force the conversations view to scroll.
3. Prefer positioning the tooltip "above" the element so it can bleed into surrounding page space reserved by the wrapped layout.

## Constraints

1. Scope is limited to the dashboard token tooltip UI behavior/styling.
2. No changes to token accounting, ingest, or warehouse schema.

## Acceptance Criteria

1. Opening the token tooltip does not create or enlarge a scrollbar on the conversations view.
2. The tooltip is fully visible (not clipped by the panel overflow).
3. Existing dashboard token-usage display/behavior otherwise remains unchanged.
