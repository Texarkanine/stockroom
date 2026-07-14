---
task_id: workspace-key
date: 2026-07-14
complexity_level: 3
---

# Reflection: workspace-key

## Summary

Added nullable `sessions.workspace_key` with an extensible per-harness ETL registry, wired Sessions by Project and ingest golden to that key, and documented the contract. Delivered to plan; QA only needed a small harness-neutrality clarification in the private encode helper.

## Requirements vs Outcome

All acceptance criteria landed: migration 0006, Cursor/Claude same-cwd convergence, different-cwd separation, NULL when underivable, metrics rollup on the key, localized strategy extension point, docs. No requirements dropped. One addition vs the written preflight blast list: warehouse open/concurrency `_HEAD_VERSION` pins and the open chokepoint’s locked snapshot also had to move to 0006.

## Plan Accuracy

Sequence (paths → migration → writer → metrics → docs → verify) was right and TDD-friendly. File list was accurate. The challenge list correctly predicted golden/schema churn and metrics basename-collide reinterpretation. The surprise was head-version pin sprawl beyond `test_migrate_runner` — same class of pin, more call sites.

## Creative Phase Review

Option C (`workspace_key` additive column) held up cleanly: identity fidelity for `project_id`, chart/SQL alignment, NULL honesty. Per-harness registry translated directly into `_WORKSPACE_KEY_STRATEGIES`. Friction was mild: creative language about “Cursor-form” encode tempted an `encode_for("cursor")` call inside the “neutral” helper; QA corrected that to leading-sep strip + `encode`.

## Build & QA Observations

Build was smooth once head pins were found. Golden regeneration and schema snapshot tooling (`STOCKROOM_UPDATE_*`) worked as designed. QA was clean except the encode-helper neutrality fix — no rework cycle.

## Cross-Phase Analysis

Preflight caught migrate_runner head pins but under-scoped sibling warehouse open/concurrency constants — a planning/preflight completeness gap that surfaced only in full-suite verify. Creative’s “Cursor-form” shorthand caused a small QA finding, not a design invalidation. Nothing forced a return to plan.

## Insights

### Technical
- Schema-head pins live in more than the migrate runner: at least `test_warehouse_open._HEAD_VERSION`, `test_warehouse_concurrency._HEAD_VERSION`, and the open chokepoint’s locked cumulative snapshot import. When adding a migration, grep for the prior head integer and prior snapshot path, not only `test_migrate_runner`.
- A “harness-neutral” path key must not call `encode_for("cursor", …)` even when the bits match today’s Cursor slug form — that reifies harness identity into a shared helper.

### Process
- Preflight blast-radius for “bump head version” should treat all `_HEAD_VERSION` / locked-snapshot consumers as one checklist item, not only the migrate-runner assertions named in the plan.
