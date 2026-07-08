---
task_id: p3-m1-stockroom-dispatcher
date: 2026-07-08
complexity_level: 2
---

# Reflection: `stockroom` dispatcher (`python -m stockroom`)

## Summary

Built the single CLI entrypoint the Phase-3 shim will exec into: `python -m stockroom <subcommand>` now dispatches `query` / `semantic` / `ingest` / `embed` / `migrate` to the existing module CLIs, and `stockroom.migrate` gained its previously-missing CLI. Delivered to plan, first-pass green through preflight, build, and QA.

## Requirements vs Outcome

Every milestone requirement landed: the tested dispatcher, the authored migrate CLI entrypoint, top-level `--help` listing subcommands, verbatim `<sub> --help` forwarding, and README dispatcher documentation. One addition beyond the milestone text: a top-level `--version` flag, added as a preflight amendment to give the m2 shim a cheap identity probe for staleness verification.

## Plan Accuracy

The plan's sequence, file list, and scope were exactly right; nothing was reordered or added. The anticipated challenges (module `prog` cosmetics, torch-free testing of `semantic`/`embed`, migrate-under-lock) were the real ones, and each mitigation held. The only in-flight discovery was the `migrate.main` → `warehouse` circular import (`warehouse.py` imports `stockroom.migrate` at load time), resolved with a function-body import — a detail, not a plan gap.

## Build & QA Observations

Build was clean: 11 subprocess tests written red-first, all green on first implementation, `make ci` fully green after one `ruff format` pass. QA found no semantic issues in the code itself; it caught two documentation gaps (the `migrate.py` module docstring didn't mention runnability, and `techContext.md` lacked a dispatcher section) — both fixed in QA.

## Insights

### Technical

- The uniform `main(argv: list[str] | None = None) -> int` shape across all module CLIs is what made first-token dispatch nearly free. Preserving that shape for any future module (e.g. a `doctor` subcommand in m3) keeps dispatcher additions one-line table entries.
- `stockroom.warehouse` imports `stockroom.migrate` at load time, so anything added to `migrate.py` that needs `warehouse` must import it lazily. Any future module that is both "imported by warehouse" and "grows a CLI over warehouse" will hit the same cycle.

### Process

- Milestone-level preflight advisories carried into the sub-run's `tasks.md` stub worked well: the m1 amendments (migrate CLI, README docs) were already in scope before planning began, so the plan phase spent no time rediscovering them.

### Million-Dollar Question

Had `python -m stockroom` been foundational from Phase 1, the per-module `__main__` guards and `prog="python -m stockroom.<mod>"` strings would never have existed — each module would ship only `main(argv)` and the dispatcher would own all program naming. That end state is still reachable cheaply (drop the guards, re-prog the parsers) if the m2 shim's naming story wants it; nothing structural blocks it.
