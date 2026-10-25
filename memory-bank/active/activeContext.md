# Active Context

## Current Task: warehouse-check-review-wording
**Phase:** PREFLIGHT - COMPLETE (FAIL (fixable))

## What Was Done

- Five preflights failed a plan that described the restore page by rules. Each round found a new state the rules did not cover.
- The operator handed the writing to Claude Opus 5.5. The plan now carries the exact text of every doc edit and of the GitHub reply.
- The restore page names four outcomes: `swapped` restores, `running` and `linked` complete first, `unreadable` goes to "Still stuck", and every other word has nothing to put back. It does not branch on every record state.
- New facts in the page: the replaced file must not be named `warehouse.copy.duckdb`, a `.wal` moves with its file, and `check.json` stays.

- Sixth preflight kept steps 4 to 9. The status list now names the no-restore words, and every other word goes to "Still stuck".

## Next Step

- Preflight the revised plan.
