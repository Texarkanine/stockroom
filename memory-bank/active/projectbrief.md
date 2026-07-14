# Project Brief

## User Story

As an advanced systems-level user or contributor, I want Architecture documentation that loads the whole Stockroom system mental model — design surface and ethos — into my head so that I can make intelligent changes to and understandings about the system (not merely operate the product).

## Use-Case(s)

### Use-Case 1

A contributor who already knows the User Guide and Contributing paths needs to understand how shim, engine, warehouse, torch, hooks, dashboard, and embeddings fit together — including unusual constraints that would otherwise invite Chesterton’s-fence removal — before changing any of those pieces.

### Use-Case 2

A maintainer writing or reviewing a change that touches distribution, scheduling, or plugin layout uses Architecture as the systems-level map, and uses Advanced / User Guide / Contributing for operational detail rather than for the design model.

## Requirements

1. Deliver the **Architecture** docs section next (Home, User Guide, and Contributing are done; Advanced follows in a later task).
2. Before writing, run a **creative exploration**: read existing docs, codebase, and related sources to find topics that *should* be in Architecture beyond the seed list.
3. Cover at least the operator’s seed topics:
   - System diagram: pieces and control flow (shim, database, plugin install, skill/engine, user)
   - Engine shipped inside the skill (skill prose + engine must stay in sync; no downloads; uv lockfile vs PyPI)
   - Shim as static entrypoint (`rectify`, `ensure-env`) for skills, schedules, and humans
   - Torch out of the lock (per-machine) — why that must be
   - Dashboard: session-hook launch, no external downloads; torch locking arrangement
   - Periodic ingest via shim (not session-start — hook timeouts / inelegant termination)
   - Hooks generally: fire-and-forget, idempotent, concurrent, fault-tolerant
   - sentence-transformers / BGE / 384-dim — what and why
4. Audience is systems-level: mental model, design surface, ethos — not product how-to.

## Constraints

1. Lead with **what is**. Include **why** only where the design is unusual enough to confuse or invite Chesterton’s-fence removal. Do not recount design diary / thought process.
2. Do not duplicate User Guide / Contributing / Advanced operational content; Architecture owns the system model, those sections own procedures.
3. Stay within `docs/` (and related nav/config as needed); no product behavior changes unless required to keep docs accurate.
4. Advanced is explicitly **out of scope** for this task (comes after Architecture).

## Acceptance Criteria

1. Architecture section presents a coherent systems mental model suitable for advanced users/contributors.
2. Seed topics are covered at the appropriate depth, with missing-but-necessary topics identified in creative exploration and included or consciously deferred with rationale.
3. Voice matches the WHAT-first / unusual-WHY-only rule.
4. Docs build cleanly (`make docs-build` or equivalent).
5. Cross-links to User Guide / Contributing / Advanced (where Advanced already exists) do not blur ownership of concerns.
