---
task_id: exact-message-text-retrieval
date: 2026-07-10
complexity_level: 2
---

# Reflection: exact-message-text-retrieval

## Summary

Added `--detail raw` as an opt-in exact-whitespace escape hatch through the existing truncate/render chokepoint, documented `--format json --detail raw` as the canonical fidelity path, and left `full` as unbounded single-line. Satisfies [issue #30](https://github.com/Texarkanine/stockroom/issues/30).

## Requirements vs Outcome

Delivered as specified: documented first-class CLI path with whitespace matching DuckDB storage; `tsv`/`table` non-raw behavior unchanged; tests cover fidelity and regression; skill handoffs updated. No requirements dropped or added beyond the planned B10 hygiene pin.

## Plan Accuracy

Plan sequence and file list were correct. Extending `DETAIL_LEVELS` alone wired both CLIs. No surprises; the anticipated challenge (docs still teaching `--detail full` as whole-field) was the real acceptance work.

## Build & QA Observations

Build was clean TDD through truncate → render → CLI → docs. QA found no substantive issues — the change is a one-branch conditional in `truncate_cell` plus documentation honesty.

## Insights

### Technical
- When a detail level is advertised as “whole field” but still mutates content (whitespace collapse), agents will distrust the warehouse. Separating *length* (`full`) from *fidelity* (`raw`) keeps table safety without lying about exact text.

### Process
- Nothing notable

### Million-Dollar Question

If exact-text retrieval had been a foundational assumption, `--detail` would have been two axes from day one (budget × fidelity), or `full` would have meant exact-and-unbounded with format-specific escaping for TSV. What we built — an additive `raw` level — is the least-disruptive version of that insight for an already-shipped orthogonal `--detail`/`--format` design.
