# Active Context

**Current Task:** Phase 2 · Milestone 1 — Embedding pipeline (`p2-embeddings-search`, sub-run m1)

**Phase:** `PREFLIGHT - COMPLETE` — PASS (with advisory), plan amended at the gate. Awaiting operator review → `/niko-build`.

## What Was Done

Classified m1 (embedding pipeline) as **Level 3**, ran the mandated load-bearing-primitive spike (vss/HNSW/persistence all green; CPU encode already proven in `o9-torch`), resolved **5** open questions in the creative phase (high confidence — `memory-bank/active/creative/`), and wrote the full L3 implementation plan to `tasks.md`. After preflight, the operator directed two design amendments (grounded in a query of the real warehouse).

Key decisions: thin `0003` index migration + chokepoint `ensure_vss`; **messages-only** embedding for m1; incremental selection + session-grained embedding cascade-delete in `ingest.writer`. **Amended at gate:** (1) **per-chunk storage** (`chunk_index 0..N-1`, max-sim dedup deferred to m2) instead of mean-pool — lossless, best long-tail recall, no schema change; (2) **model = `BAAI/bge-small-en-v1.5`** instead of all-MiniLM-L6-v2 — same 384-dim, +9 MTEB retrieval, 512-token window, no `trust_remote_code`. No `uv.lock` change; CI stays torch-free via a pure chunker + injected `FakeEncoder`, real model `importorskip`-gated.

## Next Step

🧑‍💻 **Manual gate.** Preflight passed (with advisory); plan re-affirmed after the amendments (design-only, still L3). The operator reviews the plan (`tasks.md`) and the **5** creative docs, then runs **`/niko-build`** to begin at step 1 (the pure chunker). Build-time advisories to honor: verify `ensure_vss` SET/LOAD on read-only connections; capture an index section in the `0003` golden; and confirm dense-code chunks stay within the 512-token window.
