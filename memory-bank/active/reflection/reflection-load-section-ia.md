---
task_id: load-section-ia
date: 2026-07-26
complexity_level: 2
---

# Reflection: Load section information architecture

## Summary

Turned `docs/user-guide/load/` into a real section (router index, `sources.md` for per-harness reference, generic ingest chunks in `basic.md`, `.pages` nav) and cleared the 38-warning strict-build debt from the `ingest/`→`load/` rename plus the earlier `contributing/iteration/` nest. Succeeded; zero substantive QA findings.

## Requirements vs Outcome

All six rework requirements and five acceptance criteria landed as planned. Preflight additions shipped too: A1 (stale `sr-initialize` skill path outside `docs_dir`), A2 ("Harness Sources" naming). One deliberate build deviation — enrichment heading at `###` under `## Cursor` instead of peer `##` — improved the page shape and left the slug green.

## Plan Accuracy

Sequence, file lists, and the two warning groups were right. The plan correctly pulled Group B into scope once the baseline showed acceptance criterion 5 was unreachable without it. Surprises were small: one link wrong in *both* rename dimensions at once (stale target + wrong depth), so Group A alone left 18 warnings not 19; and the enrichment heading level needed a structural call the plan had left at `##`.

## Build & QA Observations

Build was mechanical and clean once special-case retargets ran before longest-prefix bulk replace. QA found only pre-existing whitespace debris in a touched file. The content checklist (B1–B3) carried weight the build cannot — proving the split, not just the links.

## Insights

### Technical
- A link can be broken for two independent reasons at once; warning *counts* are not cause counts. Intermediate builds after each group matter when renames overlap.
- The strict docs build cannot see prose outside `docs_dir`. Shipped skill paths that cite docs need an explicit plan step (or a future hygiene test).

### Process
- Special-case non-substitutions *before* bulk path rewrite is now twice-validated (prior ADHD rework mangled `…/index.mdbackfill/`; this build avoided it by ordering).
- For docs-only work on a torch-provisioned machine, prefer `uv run --no-sync` pytest over `make test` so verification does not strip the per-machine torch install.

### Million-Dollar Question

If `load/` had been the original layout: a router index, one page per concern (basic / schedule / harness sources / backfill), and `.pages` from day one — exactly what we built. The junk-drawer index and the dual rename fallout were artifacts of incremental splits without finishing the IA. Nothing more elegant was hiding underneath.
