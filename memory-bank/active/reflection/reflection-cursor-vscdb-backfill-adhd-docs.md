---
task_id: cursor-vscdb-backfill-adhd-docs
date: 2026-07-26
complexity_level: 2
---

# Reflection: ADHD reorder of ingest / backfill user-guide pages

## Summary

Reworked the ingest and backfill user-guide pages for ADHD scan/action fit and fixed the link fallout from nesting under `ingest/backfill/`. Strict docs build green; CLI `--help` Required Order synced to four steps including embed.

## Requirements vs Outcome

All rework brief items landed: command-first ingest page with a backfill door; Required Sequence as lede with embed as step 4; Why tangent deleted; config-first + silent-miss on cursor-vscdb; nest link hygiene across `docs/`. Addition beyond the brief: CLI epilog alignment (caught in QA).

## Plan Accuracy

Sequence held. Preflight correctly expanded Step 1 after a live ripgrep — the nest had broken far more than the three ADHD pages. Surprise: ProperDocs strict mode rejects directory-trailing-slash links and wants explicit `index.md`; a naive `ingest/` → `ingest/index.md` replace mangled `ingest/backfill/` paths.

## Build & QA Observations

Build was linear once the link baseline was green. QA found one trivial contradiction (CLI still said "all three"); tightening the existing help-sequence test pinned the four-step contract.

## Insights

### Technical
- When rewriting relative links after a directory nest, replace longest path prefixes first — or assert the post-edit link set with a strict docs build before any prose rewrite.

### Process
- Elevating a step in the user-guide Required Sequence without updating the CLI `--help` epilog recreates the "docs and operator surfaces disagree" failure mode the original task already hit with `--force`→embed.

### Million-Dollar Question

Nothing notable — action-first docs with the Required Sequence as the lede is the shape that should have shipped with the first docs restructure.
