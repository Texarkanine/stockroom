# Project Brief

## User Story

As a contributor with a local checkout already wired (see Local workflow), I want a clear day-to-day Development guide so that I know how to change the engine, Torch, docs site, dashboard, and skills without re-learning the enter/exit ritual.

## Use-Case(s)

### Use-Case 1

A contributor finishes [Local workflow](../../docs/contributing/local-workflow.md), opens Development, and finds prerequisites plus ordered guidance for engine / Torch / docs / dashboard / skills work, with an accurate `make` target reference.

### Use-Case 2

A contributor needs to try a new Torch index or restore torch after `make sync`, and Development points them at the torch-safe contract and operator remedies without duplicating the full localdev round-trip.

## Requirements

1. Rework `docs/contributing/development.md` assuming local setup is done; link to Local workflow for enter/verify/exit.
2. Cover, in a sane order: prerequisites; engine changes; Torch (including trying new Torches); docs site; dashboard; skills.
3. Refresh the `make` targets table/list to match the current Makefile and this guide’s day-to-day focus.
4. Keep localdev atom narrative owned by `local-workflow.md`; Development should not re-own the rip-it-out story.

## Constraints

1. Presentation quality consistent with accepted Contributing / user-guide bar (including markdown style rules).
2. End-user install remains `sr-initialize` / marketplace — Contributing must not present `make`/`uv` as bootstrap for operators.
3. Prefer pointers over duplication for torch operator contract (`docs/user-guide/troubleshooting/torch.md`) and localdev round-trip.

## Acceptance Criteria

1. `development.md` is structured around day-to-day develop surfaces (prereqs → engine → torch → docs → dashboard → skills), not the localdev enter/exit ritual.
2. `make` target listing matches current Makefile help/semantics for targets relevant to this page.
3. Cross-links to Local workflow and Torch troubleshooting are correct and non-redundant where possible.
4. Docs build / preview still works for the contributing section.
