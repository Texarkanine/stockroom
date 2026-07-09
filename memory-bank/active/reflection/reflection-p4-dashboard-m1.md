---
task_id: p4-dashboard-m1
date: 2026-07-09
complexity_level: 3
---

# Reflection: Dashboard metrics API server

## Summary

Milestone m1 delivered the complete local dashboard backend: observation-time
schema and ingest support, a non-migrating read chokepoint, eight metric
endpoints, loopback HTTP/static serving, and idempotent CLI startup. The first
QA review found a localized transport-policy bug and coverage/documentation
gaps; remediation passed the full 402-test project gate and the second review.

## Requirements vs Outcome

All planned requirements shipped. The API supports repeated harness filters,
inclusive/exclusive ISO windows with endpoint-owned defaults, recent sessions,
all-time wrapped metrics, stable empty shapes, actionable warehouse refusals,
and a 500-session response cap. Cursor sessions use transcript mtime as an
honest last-activity fallback, while first-observation message time survives
re-ingest.

No product requirement was dropped or descoped. Two substrate additions were
larger than the milestone title suggested but were required by the accepted
design: migration `0004` and ingest carry-forward of `first_seen_at`. Routine
migration-head test updates were also added outside the original file list.

## Plan Accuracy

The nine-step sequence held: schema before ingest, ingest before warehouse
opening, metrics before transport, transport before CLI, then full verification.
Module boundaries and the two creative decisions remained valid throughout.

The plan accurately predicted stale-schema refusal, writer-lock degradation,
source-mtime portability, and the port-probe race. It missed two implementation
hazards:

- Expanding a partial HTTP window to 30 days looked like neutral parsing but
  silently overrode trends and sessions policy.
- Calendar label counts are not equivalent to elapsed-day durations when both
  displayed boundary dates are included.

The planned file list also omitted existing tests whose migration-head constants
necessarily changed. Scope and level remained accurate: this was a genuine L3
feature within an L4 milestone sequence, and no rearchitecture was required.

## Creative Phase Review

The session-time decision held up. `COALESCE(started_at, source_mtime)` made
Cursor visible without fabricating authored timestamps, and the separate
`first_seen_at` observation grain preserved future recap value. The cost is
explicit and acceptable: old rows remain NULL until observed, and Cursor daily
metrics represent last transcript activity rather than session start.

The non-migrating-open decision also held. `open_current()` kept migration
policy in the warehouse module, allowed the hook-launched dashboard to start
without a warehouse, and produced clean missing/stale/busy 503 responses.
The HTTP stale anti-gate test demonstrated that refusal does not mutate schema.

Neither creative decision caused the QA failure. The failure arose one layer
above them, where the server accidentally assumed ownership of metric defaults.

## Build & QA Observations

TDD made the schema, carry-forward, locking, metric, server, and CLI contracts
incrementally tractable. Existing injection seams made real HTTP tests possible
without introducing a framework or mocking DuckDB internals.

QA caught a substantive behavior error that the first green suite had not
encoded: `until`-only trends became 30 days and `until`-only sessions acquired
an unintended lower bound. It also correctly treated promised cross-cutting
coverage and endpoint-grain documentation as completion requirements. The fix
was small once ownership was clear: parse individual bounds in transport and
leave default construction to metrics.

The full gate exposed pre-existing tooling debt twice: the Makefile's exact sync
removes the intentionally out-of-lock Torch installation. Restoring the
confirmed `cu126` wheel and running the production encoder smoke preserved the
machine environment, but the prerequisite should become torch-safe separately.

## Cross-Phase Analysis

Creative exploration prevented two expensive mistakes before build: excluding
most Cursor history due to absent authored timestamps, and allowing a
session-start read surface to trigger migration. Preflight also caught the
schema-map update, harness enumeration, response cap, loopback binding, and
clean-error requirements before they became review findings.

The QA failure traces to a test-plan execution gap rather than a design gap.
Planning explicitly assigned defaults per endpoint and called for cross-cutting
window tests, but the first server tests covered complete bounds and generic
routing rather than partial bounds. Once the missing transport-boundary example
was added, the wrong policy became immediately visible.

For the enclosing L4 project, m1 validates the intended milestone split: the
backend contract is independently testable and stable before m2 adds a visual
client. It also establishes that future local read surfaces should reuse
`open_current()` instead of bypassing warehouse policy.

## Insights

### Technical

- Parse syntax at transport boundaries; construct behavioral defaults in the
  endpoint that owns them. A generic default is policy, not parsing.
- Fixed calendar-series shapes should derive their first bucket from the last
  instant included by an exclusive end, not from a raw duration subtraction.
- A non-migrating read chokepoint is a reusable architectural capability, not a
  dashboard exception: it cleanly separates availability from schema mutation.
- Observation-derived data must be captured and carried forward because it
  cannot be reconstructed from prunable source history.

### Process

- Cross-cutting requirements need at least one boundary-level test combining
  transport and domain behavior; isolated unit coverage can leave ownership
  errors invisible.
- File-impact planning should include a migration-head sweep whenever a numbered
  migration is added.
- Estimation was accurate at Level 3, but verification cost was understated
  because the exact-sync/Torch conflict adds a restore-and-smoke cycle to every
  full gate until the Makefile is corrected.
