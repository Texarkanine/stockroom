---
task_id: p2-embeddings-search-m3.5
date: 2026-06-29
complexity_level: 2
---

# Reflection: Output format defaults (`--format`)

## Summary

Introduced a shared `stockroom.render` presentation chokepoint exposing `format_query` / `format_semantic` over `tsv` (new default) / `json` / `table`, absorbing the two relocated private renderers and applying the m3 `truncate_cell` policy uniformly across every format. Both read-surface CLIs gained `--format`; library return types were untouched. Succeeded cleanly: `make ci` green at 266 passed / 2 skipped, QA PASS with no fixes.

## Requirements vs Outcome

Delivered every requirement of the milestone and the `print-for-who.md` decision record (PFW1–PFW7): `--format tsv|json|table` (default `tsv`), no count trailer in `tsv`/`json`, `jq`-friendly JSON, `table` preserving the prior human output, `--detail` applied in every format via the unchanged `truncate.truncate_cell`, and the library print boundary untouched. No requirements were dropped or added; the only build-time addition was the preflight TDD-ordering amendment (query CLI tests written before the `query.py` wiring), which changed sequencing, not scope.

## Plan Accuracy

The plan was accurate end-to-end. The file list, the `TYPE_CHECKING`-only import to break the `render ↔ query/semantic` cycle, the "move the two table renderers, don't merge them" boundary, and the JSON type-handling decisions all held exactly as written. The one identified-and-managed risk that actually materialized was the `tsv`-default flip breaking the two semantic trailer-asserting CLI tests — anticipated in the plan and resolved as planned (assert tsv shape / pin to `--format table`). No surprises came from elsewhere. The preflight catch (query CLI tests two steps downstream of their code) was a real, small TDD-ordering improvement.

## Build & QA Observations

Build was smooth and mechanical: stub→red→green on `render`, then thin per-surface wiring, each unit test-first. The relocated renderers moved verbatim, so the table-format tests passed unchanged once re-pointed at `render`. The only deviation was cosmetic `ruff format` line-wrapping in the two new files. QA was clean — no trivial fixes — and confirmed the duplication is the plan-sanctioned deferred consolidation rather than new debris.

## Insights

### Technical
- Relocating `_format_table`/`_format_hits` into `render` made the long-standing "two renderers duplicate column alignment" insight *concrete and local*: the duplicated `widths`/`_line` plus the semantic row projection and the `1.0 - distance` score computation now sit side-by-side in one module. The clean consolidation (`render_table(columns, rows, *, detail)` owning alignment and taking pre-projected rows) is now a single-file refactor — the natural next milestone-adjacent cleanup, and the reason a piecemeal DRY now would be wasted.
- TSV structural safety falls out of the m3 truncation policy for free: `truncate_cell`'s `" ".join(value.split())` collapses tabs/newlines at every detail level, so no raw delimiter can corrupt a field — the format needed zero extra escaping. A capability built for one concern (context-safe width) silently satisfied another (delimiter safety).

### Process
- The `TYPE_CHECKING`-only import + `from __future__ import annotations` is the right reflex whenever a new shared/lower layer needs to name types defined in the higher layers that will call it; planning the one-way runtime edge up front avoided any cycle iteration during build.
- Preflight's per-unit TDD-ordering check earned its keep on a near-trivial plan: it caught CLI code scheduled two steps before its tests and fixed it before any code was written.

### Million-Dollar Question

Had "every read surface renders through one presentation chokepoint, in a selectable format" been a foundational assumption, `query` and `semantic` would never have grown private `_format_*` renderers at all: a single `stockroom.render` with one `render_table(columns, rows, *, detail)` (owning alignment + truncation) plus the `tsv`/`json` serializers would have existed from the first read surface, and each surface's `main` would only project its domain object to `(columns, rows)` and call `render`. We've now landed ~90% of that shape; the remaining 10% — folding the two table bodies into one `render_table` — is the deferred consolidation this milestone deliberately left as the next clean step.
