---
task_id: pr92-coderabbit-fixes
date: 2026-07-26
complexity_level: 2
---

# Reflection: PR #92 CodeRabbit selected fixes

## Summary

Landed nine judged CodeRabbit findings on PR #92: seven documentation corrections and two `cursor_vscdb` stability fixes (`open_readonly` URI encode + close failed rung; `candidates` → `BackfillError`). Succeeded; QA found only a docstring polish.

## Requirements vs Outcome

Every operator-selected item shipped. Dismissed items (US “parameterized”, creative rewrites, tasks.md lint, conftest re-entrancy) stayed untouched. Original brief AC #7 (API tokens unavailable from vscdb) is finally on the user-guide page.

## Plan Accuracy

Sequence held: adapter TDD before docs. One test-shape surprise — `sqlite3.Connection.close` is read-only, so the leak test needed a tiny proxy rather than monkeypatching the method. `Path.as_uri()` worked as planned; existing ladder substring assertions did not need updates.

## Build & QA Observations

The `?`-in-path bug fails *silently* (wrong/empty URI target) rather than loudly — the encoding test’s first red was `no such table`, which is the real operator-facing failure mode. QA was clean beyond moving the URI/close notes into the `open_readonly` docstring.

## Insights

### Technical
- SQLite `file:` URIs treat an unencoded `?` in the path as the query delimiter; the symptom is a successful open of the wrong database, not a connect error.
- CPython’s `sqlite3.Connection.close` cannot be assigned; observe close via a proxy when testing resource cleanup.

### Process
- Judging first (`/pr-feedback-judge`) then reworking only the selected dispositions kept scope tight — nine fixes without absorbing the bot’s full laundry list.

### Million-Dollar Question

If `open_readonly` had used `Path.as_uri()` and typed every sqlite failure from day one, items 13–14 would never have existed. The docs items are ordinary copy debt from the ADHD/IA reworks. Nothing more elegant was required than what we shipped.
