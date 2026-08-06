# Project Brief

## User Story

As a dashboard user, I want the Sessions conversation list to read in a sensible chronological order around the ellipsis fold so that I can scan recent and older activity without being confused by reverse ordering below the fold.

## Use-Case(s)

### Use-Case 1

On the metrics dashboard Sessions panel, when there are more than 20 matching conversations, the list shows 10 newest, an ellipsis (`… N more`), then a bottom block. That bottom block should not feel incorrectly oldest-first relative to expected reading order.

### Use-Case 2

Investigate and confirm whether the observed oldest-first ordering below the fold is a bug or intentional design; only change behavior if it is wrong.

## Requirements

1. Investigate the dashboard Sessions list ordering below the ellipsis fold.
2. Confirm whether oldest-first below the fold is incorrect.
3. If it is a bug, fix it with tests and open a draft PR.
4. If it is intentional/correct, document the finding and stop without a behavioral change (still report clearly).

## Constraints

1. Prefer minimum change; do not redesign the Sessions panel.
2. Follow TDD for any executable behavior change.
3. Open a draft PR when a fix is needed.

## Acceptance Criteria

1. Root cause of the observed ordering is identified and stated.
2. Either a fix lands with tests proving the corrected order, or investigation concludes the current order is correct by design with evidence.
3. If a fix is made, a draft PR is opened.
