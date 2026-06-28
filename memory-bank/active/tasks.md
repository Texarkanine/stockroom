# Current Task: Phase 2 · Milestone 1 — Embedding pipeline (`p2-embeddings-search`, sub-run m1)

**Complexity:** Level 3

The task checklist is populated by the Level 3 PLAN phase. The deliverable is the
first milestone of the Phase 2 L4 project, per `memory-bank/active/milestones.md`:

> **Embedding pipeline** — VSS/HNSW index migration (`0003`, cosine, experimental
> persistence on) plus a `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim)
> embedder with chunk-and-mean-pool, GPU-or-CPU device selection, `FLOAT[384]`
> writes through the chokepoint, and incremental re-embed of only
> un-embedded/changed content.

Binding sub-run findings (from `milestones.md` "Preflight findings") that the
plan/creative phase must resolve:

- Embedder must be unit-testable **without torch** (CI is torch-free) — favor an injected-encoder pattern.
- VSS extension provisioning must respect the **offline/supply-chain posture** (no implicit network `INSTALL`).
- `embeddings.owner_id` **grain** is ambiguous for `tool_calls` — decide keying before writing vectors.
- New migration `0003` is a **test-suite-wide event** — budget migration-head + golden-snapshot updates.
- **Open with a load-bearing-primitive spike**: offline `vss`, HNSW cosine + live-delete persistence, CPU `all-MiniLM-L6-v2` encode.
