# Task: architecture-docs

* Task ID: architecture-docs
* Complexity: Level 3
* Type: documentation feature

Human Architecture docs section: systems-level mental model for advanced users/contributors (WHAT-first voice; Advanced deferred).

## Component Analysis

### Affected Components
- `docs/architecture/` — stub overview (`index.md`, `.pages`) → rewrite into real Architecture section
- `docs/.pages` — top-level nav already lists `architecture`; may need order/label tweaks only
- Cross-links from `docs/index.md`, Contributing, User Guide, Advanced stubs — ownership pointers only; no rewrite of those sections
- Agent `skills/sr-search/references/system-model.md` — related audience (agents); must not fork or replace; Architecture may point at it, not duplicate as SSOT
- Maintainer `memory-bank/systemPatterns.md` — briefing altitude; Architecture is human site, not a dump of MB

### Cross-Module Dependencies
- Architecture → User Guide / Contributing / Advanced: outbound links for procedures; Architecture owns design model only
- Architecture ← codebase / systemPatterns / system-model: sources of truth for WHAT; prose synthesizes, does not invent

### Boundary Changes
- Public docs IA under `docs/architecture/` (new pages possible)
- No product/runtime interface changes

### Invariants & Constraints
- WHAT-first; WHY only for unusual / Chesterton’s-fence designs
- Do not duplicate operational how-to owned elsewhere
- Advanced out of scope this task
- Docs must build (`make docs-build`)
- Seed topics must be covered at appropriate depth

## Open Questions

- [ ] **Architecture scope & ownership** — Which systems topics belong in human Architecture vs agent `system-model.md` vs User Guide / Contributing / Advanced? What beyond the seed list must Architecture cover, and what must it deliberately exclude?
  - Ambiguous because: three overlapping “system model” audiences already exist; seed list is incomplete by operator admission; risk of forking or bloating.
  - Constraints: systems-level audience; WHAT-first; no product how-to; Advanced deferred; agent system-model remains agent SSOT for doctrines shipped with the plugin.
- [ ] **Architecture page IA** — Given the topic set, how should `docs/architecture/` be structured (single long page vs overview + satellites; nav labels; depth per page)?
  - Ambiguous because: Contributing uses multi-page surface-first IA; current Architecture is a thin stub; topic count from Q1 will drive structure.
  - Constraints: loadable mental model; scannable nav; no dashboard-of-docs clutter; consistent with properdocs / existing section patterns.

## Status

- [x] Component analysis (draft)
- [ ] Open questions resolved
- [ ] Test planning complete (TDD)
- [ ] Implementation plan complete
- [ ] Technology validation complete
- [ ] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
