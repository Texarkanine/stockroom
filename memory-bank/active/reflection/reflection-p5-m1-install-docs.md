---
task_id: p5-m1-install-docs
date: 2026-07-09
complexity_level: 2
---

# Reflection: p5-m1-install-docs

## Summary

Shipped best-effort README install/usage docs (marketplace path + Cursor/Claude local/dev loaders, skill invocation table) and removed docstring/prose packaging pins. Live marketplace install and empirical invocation proof were deliberately deferred to m2/m3.

## Requirements vs Outcome

Original L4/m1 wording asked for empirical verification and a packaging/doc contract. Operator decisions during build dropped both: no CI pins on docs, and no live install proof until stockroom is in `txrk9-agent-plugins` and exercised from `main`. Delivered docs match the amended brief; deferred work is explicit in README, milestones, and progress.

## Plan Accuracy

The plan correctly identified README as the doc surface and dual manifests as already done. It was wrong about (1) needing a docstring contract and (2) being able to validate "manual install" as a first-class end-user path without a marketplace — Cursor's folder picker and Claude's permanent install are marketplace-shaped. Local loaders (`~/.cursor/plugins/local/`, `claude --plugin-dir`) are the real pre-marketplace story.

## Build & QA Observations

Build was mostly documentation plus deleting two prose-pin tests. QA was clean: no debris, no missing amended requirements. Full suite stayed green.

## Insights

### Technical
- Cursor "add plugins from folder" expects `marketplace.json`, not `plugin.json`. Stockroom correctly has only plugin manifests; the catalog belongs in `txrk9-agent-plugins`.
- Claude's durable install path is also marketplace-shaped; `--plugin-dir` is session/dev, not the end-user story.

### Process
- Docstring/prose packaging tests (README pins, planning-doc port pins) fight doc authorship. Prefer human-owned docs and reserve packaging tests for real install artifacts (manifests, hooks, release-please).

### Million-Dollar Question

Treat marketplace listing as a prerequisite for any "install works" claim, and write Phase-5 docs from day one as "intended marketplace path + honest local/dev loaders," without inventing a third install UX or CI-locking prose. That is essentially what we ended with after the mid-build course correction.
