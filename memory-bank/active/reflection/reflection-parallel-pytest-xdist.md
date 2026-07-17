---
task_id: parallel-pytest-xdist
date: 2026-07-17
complexity_level: 2
---

# Reflection: parallel-pytest-xdist

## Summary

Locked `pytest-xdist` and defaulted engine pytest to process workers via `addopts = ["-n", "auto"]`. Full suite stayed green under 16 workers; Make/CI needed no flag edits.

## Requirements vs Outcome

Delivered as briefed: locked dep, inherited parallelism for Make/CI, isolation held, contributor docs + techContext updated. Nothing descoped; JS parallelism stayed out of scope by design.

## Plan Accuracy

Plan sequence held. The main bet — existing `warehouse_home` / `tmp_path` isolation is enough for xdist — was correct; Challenge “serialize concurrency tests if flake” did not fire. No isolation patches.

## Build & QA Observations

Build was smooth: red contract tests → lock + addopts → full `make test` (~19s for 586 pytest). QA only trimmed redundant asserts. Worker startup cost is noticeable on tiny targeted runs; the full suite amortizes it.

## Insights

### Technical
- Put parallelism in pytest `addopts`, not Makefile/CI flags — one SSOT, zero workflow-file churn, ad-hoc `uv run pytest` stays parallel too.

### Process
- Nothing notable

### Million-Dollar Question

Same shape: process workers as a project pytest default from day one, with contracts in the lock-hermetic suite. No deeper redesign.
