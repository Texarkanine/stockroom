# Active Context

**Current Task:** Phase 2 · Milestone 1 — Embedding pipeline (`p2-embeddings-search`, sub-run m1)

**Phase:** `PREFLIGHT - COMPLETE` — PASS (with advisory). Awaiting operator review → `/niko-build`.

## What Was Done

Classified m1 (embedding pipeline) as **Level 3**, ran the mandated load-bearing-primitive spike (vss/HNSW/persistence all green; CPU encode already proven in `o9-torch`), resolved all 3 open questions in the creative phase (high confidence — `memory-bank/active/creative/`), and wrote the full L3 implementation plan to `tasks.md`.

Key decisions: thin `0003` index migration + chokepoint `ensure_vss` (keeps network `INSTALL` off the runtime hot path); **messages-only** embedding for m1; incremental selection (new + current-model) **plus** a session-grained embedding cascade-delete in `ingest.writer` (changed detection, no schema column). No `uv.lock` change; CI stays torch-free via a pure chunker + injected `FakeEncoder`, with the real model `importorskip`-gated.

## Next Step

🧑‍💻 **Manual gate.** Preflight passed (with advisory). The operator reviews the plan (`tasks.md`) and the 3 creative docs, then runs **`/niko-build`** to begin implementation at step 1 (the pure chunker). Two build-time advisories to honor: verify `ensure_vss` SET/LOAD on read-only connections, and capture an index section in the `0003` golden.
