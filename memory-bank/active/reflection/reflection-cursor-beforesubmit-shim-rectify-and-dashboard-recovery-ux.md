---
task_id: cursor-beforesubmit-shim-rectify-and-dashboard-recovery-ux
date: 2026-07-30
complexity_level: 3
---

# Reflection: cursor-beforesubmit-shim-rectify-and-dashboard-recovery-ux

## Summary

Shipped Cursor path-only `beforeSubmitPrompt` suspenders (keep full `sessionStart`) and an in-memory dashboard diagnostic HTML page for static/document misses. Build and QA passed cleanly against the MVP plan.

## Requirements vs Outcome

Delivered all acceptance criteria: non-blocking path-only rectify on submit, unchanged sessionStart + no workspaceOpen, diagnostic HTML with shim-first ordered remedies and online troubleshooting links, API/session JSON 404 preserved. Operator MVP descoped the shim-vs-replace classifier before build; that descope was intentional and reflected in tests (content contracts, not a classifier matrix).

## Plan Accuracy

The six-step TDD plan held: shim flag → hook → recovery module → server wire → docs → full suite. File list and challenge list were accurate (especially “do not convert `_not_found()` wholesale”). No reordering needed. The only scope change was the pre-build MVP amendment (classifier → one page), which preflight re-validated.

## Creative Phase Review

- **beforeSubmitPrompt trim (Option B):** Held up cleanly — `ensure_env` kwarg + `--path-only` mapped 1:1 to the continue-first shell sketch; packaging tests locked the contract.
- **Dashboard recovery (Option A → MVP Option B):** The original classifier design was correctly deferred. Building one page was faster and avoided false `--replace` advice; ordered-remedy content tests encode the hard rule without FS probes.

## Build & QA Observations

Build was straightforward once MVP was locked. Existing “rectify always ensures” / “exactly one sessionStart” tests needed deliberate extension rather than blind preservation — anticipated in the plan. QA found no substantive issues; only a non-blocking note about duplicated test helpers.

## Cross-Phase Analysis

Operator MVP amendment after preflight was the load-bearing cross-phase moment: it prevented building a classifier that path-only suspenders would have made half-wrong. Preflight’s insistence on keeping `_not_found()` JSON-only prevented an easy SPA break. Creative docs remained useful as implementation notes after the amendment.

## Insights

### Technical

- Healthy `ensure_engine_env` still shells `uv sync --check` — too expensive for every-prompt frequency; path-only vs full rectify is a real split, not a premature optimization.
- A running dashboard process can still serve recovery HTML after the plugin tree is deleted **only if** recovery code was imported at process start — in-memory string constants are the whole strategy.

### Process

- Descoping a clever classifier to one honest page *after* creative but *before* build (with preflight re-validation) was cheaper than discovering false `--replace` advice in QA.
- Nothing notable beyond that — L3 plan → preflight → build → QA flowed without rework.
