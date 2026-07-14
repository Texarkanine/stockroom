---
task_id: polish-readme-sales-pitch
complexity_level: 2
date: 2026-07-14
status: completed
---

# TASK ARCHIVE: polish-readme-sales-pitch

## SUMMARY

Polished the root [README.md](../../../README.md) into a sales-forward GitHub first impression with published docs-site links. Build initially shipped pitch + three `docs/img/` screenshots + skills table + license; operator post-reflect lean kept the pitch/quickstart/docs-site routing and dropped the embedded graphics, skills table, and license section for a tighter page.

## REQUIREMENTS

1. Sales-forward README (not a raw `docs/` index).
2. Graphics where they fit (reuse `docs/img/` or request shots).
3. Prefer `https://texarkanine.github.io/stockroom/` for reader deep links.
4. Accurate Cursor/Claude quickstart.
5. Preserve licensing pointer when present.

## IMPLEMENTATION

| Area | Paths |
| --- | --- |
| README | `README.md` |
| Assets considered | `docs/img/stockroom-dashboard-*.png`, `stockroom-duckdb-query.png` (reused in build; removed in operator lean) |

Site URLs follow the same trailing-slash style as `CONTRIBUTING.md`. No `docs/` site redesign.

## TESTING

Docs-only acceptance checklist (B1–B8) against the build README: all green. No pytest/js suite owns README. `make docs-build` skipped (`docs/` untouched). Operator lean accepted as final reader shape for the PR.

## LESSONS LEARNED

- Relative `docs/img/` paths work on GitHub without copying assets.
- For README L2s, an explicit baseline-red checklist is enough TDD.
- Operator may prefer a leaner sell-and-route page than the maxed graphics draft — archive the final shape, not only the build snapshot.

## PROCESS IMPROVEMENTS

None beyond noting post-reflect operator edits belong in the archive outcome when they redefine the deliverable.

## TECHNICAL IMPROVEMENTS

None required for this docs task.

## NEXT STEPS

None for this task. Type `/niko` for new work.
