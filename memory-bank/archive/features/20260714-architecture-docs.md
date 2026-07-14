---
task_id: architecture-docs
complexity_level: 3
date: 2026-07-14
status: completed
---

# TASK ARCHIVE: architecture-docs

## SUMMARY

Delivered a five-page Architecture systems atlas for advanced users/contributors: overview (control-flow map + change surfaces) plus Packaging, Lifecycle, Warehouse, and Embeddings. Voice is WHAT-first with WHY only for unusual / Chesterton’s-fence designs. Procedures stay outbound to User Guide / Contributing / Advanced; agent `system-model.md` is linked, not forked. Strict `make docs-build` green. Post-reflect polish locked the expanded subgraph control-flow diagram, promoted shim/heal as Entrypoint deep links on Packaging, and regrouped headings to fix incorrect joins/splits.

## REQUIREMENTS

From the project brief:

1. Deliver the **Architecture** docs section (Advanced deferred).
2. Run creative exploration before writing to find topics beyond the seed list.
3. Cover seed topics: control-flow map; engine-in-skill + lock hermeticity; shim `rectify`/`ensure-env`; torch out of lock; dashboard hook launch / offline / torch-safe; scheduled ingest (not session-start); hook doctrine; sentence-transformers / BGE / 384-dim.
4. Audience is systems-level mental model — not product how-to.
5. Constraints: WHAT-first; no ownership blur with UG/Contributing/Advanced; docs-only; Advanced out of scope.
6. Acceptance: coherent atlas; seed + inventory topics at correct depth; voice holds; `make docs-build`; ownership pointers clean.

## IMPLEMENTATION

### Approach

Docs-only L3 with two creatives → plan → preflight → TDD-style content checklist → stubs → fill → strict build → QA → reflect → post-reflect polish.

### Key files

| Area | Paths |
| --- | --- |
| Atlas | `docs/architecture/index.md`, `packaging.md`, `lifecycle.md`, `warehouse.md`, `embeddings.md` |
| Nav | `docs/architecture/.pages` (Overview → Packaging → Lifecycle → Warehouse → Embeddings) |
| Entry pointers | Light cross-links from Home / Contributing / Advanced as needed |
| Persistent MB | Contributing path renames reconciled in `systemPatterns.md` / `techContext.md` (rename debt from prior task) |

### Canonical control-flow (pinned on index)

Actors (Human, Agent via `sr-*`, session-start hooks, nightly schedule) → shim → engine; logs ingest into warehouse; embeddings write vectors that live in warehouse; dashboard RO-reads warehouse via `open_current`.

### Creative decisions (inlined)

**Scope & ownership — selected C: systems atlas with inclusion bar**

- Options: A mirror `systemPatterns`; B seed-only; C atlas with inclusion bar.
- Inclusion bar: on the control-flow map, OR unusual Chesterton-fence constraint, OR unsafe to change without knowing it.
- Exclusions held: install/heal recipes, Make loops, CLI tables, skill flags, licensing deep-dive, schema DDL dumps.
- Relationship: Architecture = human atlas; `system-model.md` = agent compact form (link); `systemPatterns.md` = maintainer briefing (mention, don’t mirror).
- Tradeoff: intentional overlap with system-model on packaging/torch/truncation/identity, managed by audience pointers — not a forced single SSOT across human+agent.

**Page IA — selected C: overview + thematic clusters**

- Options: A single long page; B fine-grained (~10–15 pages); C five thematic pages matching Contributing grain.
- Page contracts: index = map/audience/change-surfaces; packaging = how code arrives/runs; lifecycle = when things fire; warehouse / embeddings = data plane.
- Index must frame satellites as atlas body (“read these to load the model”), not optional appendices — reinforced by change-surfaces table (preflight advisory).

### Post-reflect polish

- Operator-chosen expanded subgraph Mermaid (actors / code / sources / store / viz).
- Packaging: shim + heal as deep-linkable Entrypoint sections near top; Plugin layout grouping.
- Heading regroup + mismatch rectification: timestamps ≠ migrations; kept-fields out of ETL; ingest under warehouse-is; read-time rendering ≠ search-surface; hooks JSON shape → Lifecycle rendered artifacts.
- Shim/heal stay on Packaging (not own pages / not index doctrines); leaf anchors preserved.

## TESTING

Docs-only verification (no new pytest):

1. **Build checklist** — page-by-page claim checklist in tasks (seed + inventory topics); all items checked after prose landed.
2. **`make docs-build`** — strict PASS (also after QA fix and post-reflect polish).
3. **`/niko-preflight`** — PASS; amended plan for checklist → stubs → fill → build ordering; advisory change-surfaces table on index.
4. **`/niko-qa`** — PASS; one trivial accuracy fix (hook timeouts are harness-agnostic, not Cursor-only).
5. **Exclusions / ownership spot-check** — Architecture does not re-own Contributing Iteration, UG torch troubleshooting, or Advanced CLI recipes.

Side effect during build: stale renamed Contributing links elsewhere on the site blocked strict build — fixed surgically without widening Architecture content scope.

## LESSONS LEARNED

### Technical

- Human Architecture and agent `system-model.md` should stay deliberately overlapping on packaging/torch/truncation/identity — managed by audience pointers, not by forcing a single SSOT.
- Strict properdocs is an integration test for *site-wide* link hygiene; Architecture work can unblock on stale links elsewhere without absorbing that content into Architecture.
- Forced joins from leftover H2s (timestamps+migrations, rendering under search surfaces) are easy to inherit when regrouping — scan after regroup.

### Process

- Docs TDD for prose: an unchecked page-by-page claim checklist is an effective failing-test stand-in when pytest does not apply.
- Preflight’s checklist-before-prose amendment prevents “write then invent tests.”
- Do not parallelize memory-bank edits with `git add`/`commit` in the same turn — race risk (observed: empty `tasks.md` blob; restored in follow-up commit).

### Creative phase held

- Systems atlas inclusion bar kept Architecture from becoming a second systemPatterns or a procedure dump.
- Thematic clusters matched Contributing grain; five pages were the right cut for ~20 include topics.

## PROCESS IMPROVEMENTS

- Keep post-reflect operator polish in the same task until archive rather than opening a new task for diagram/heading tweaks alone.
- When a prior docs rename leaves broken cross-links, treat strict build failures as site-wide hygiene and fix surgically — don’t expand the current task’s content scope.

## TECHNICAL IMPROVEMENTS

None required for this docs task beyond the Architecture corpus itself. Persistent MB Contributing path names were reconciled during reflect; further “Development” → “Iteration” prose cleanup can be surgical when next touched.

## NEXT STEPS

None for this task. Advanced docs remain deferred (explicitly out of scope). Type `/niko` to begin the next task.
