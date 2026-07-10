---
task_id: dashboard-polish-m1-top-controls
date: 2026-07-10
complexity_level: 3
---

# Reflection: dashboard-polish-m1-top-controls

## Summary

Delivered L4 milestone m1: top-bar date-range presets wired to windowed `since`/`until` with honest panel labels, plus Aggregate/Compare restyled as one segmented exclusive control. Build and QA both passed with no plan deviations.

## Requirements vs Outcome

All m1 requirements from the plan and issues #4/#5 were met: preset exclusive control (`Default | 7d | 30d | 90d | 1y`), bounds on all endpoints except Wrapped, prior-window deltas via existing server behavior, dynamic panel-range/overview aria labels, segmented mode visuals without mode-semantics/API changes. Nothing was descoped; nothing extra shipped (no URL sync, persistence, or calendar).

## Plan Accuracy

The five-step plan (data → core → static → adapter → verify) matched the real dependency order and needed no reordering. File list and `options.window` API shape from preflight were correct. Anticipated challenges (dishonest labels, Wrapped filtering, crowded controls) were handled by the planned helpers and shared `.segmented` styling; no surprise blockers appeared during build.

## Creative Phase Review

Option A (presets + Default) translated cleanly: fieldset radios, `daterange` → refetch, central bound formatting, label helper keyed by preset. No friction converting the creative notes into code. Deferring free-form calendar / URL sync kept the state shape `{ since, until } | null` future-proof without overbuilding m1.

## Build & QA Observations

TDD on steps 1–3 made the adapter step thin and low-risk. Full `make ci` was green on first verification pass. QA found only trivial surface issues (unused exports, JSDoc wording) — no substantive gaps between plan and implementation.

## Cross-Phase Analysis

Preflight’s amendments (explicit TDD ordering; `options.window` instead of a new positional arg) prevented API drift during build. Creative’s Default-omits-bounds decision avoided a first-paint “regression” on trends defaults. Keeping business logic out of `dashboard.mjs` meant QA had little adapter surface to criticize.

## Insights

### Technical
- Dashboard presentation policy (mode, date-range labels, bounds resolution) belongs in `dashboard-core.mjs` / `dashboard-data.mjs`; the DOM adapter should only wire events and apply already-tested helpers — that split kept m1 reviewable and regression-safe.

### Process
- For control-strip UI work that spans HTML contracts + pure JS + thin adapter, the plan’s “static contracts as their own TDD step before adapter glue” paid off: markup/CSS landed with pytest green before any DOM wiring.
