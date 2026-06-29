# Architecture Decision: Embedding Model (at fixed 384-dim)

## Requirements & Constraints

Ranked quality attributes:

1. **Retrieval quality** on agentic-coding conversation text — the whole point of semantic search.
2. **CPU throughput** — the binding hardware target is a CPU-only CI/cloud Linux box (this PC has a GTX 1070, the M4 has MPS, datacenter GPUs are fine; CPU is the floor). Favors a small model.
3. **Supply-chain / offline posture** — no `trust_remote_code` (no arbitrary model code execution); permissive license; weights provisionable once and run from local cache.
4. **Schema stability** — `embeddings.vector` is `FLOAT[384]` in `0001`. **Staying at 384-dim avoids a migration + full re-embed.** This is a hard scoping constraint: candidates must be 384-dim.
5. **Cross-milestone contract simplicity** — whatever query/passage prefix convention the model needs must be coordinated between m1 (passage embedding) and m2 (query embedding).

Out of scope: changing the 384-dim width (would force a schema migration and re-embed — explicitly avoided); GPU-only large models (violate the CPU floor).

## Components

The `EMBED_MODEL` constant in `stockroom.embed`, the `MiniLMEncoder`→ generic encoder, and the (m2) query-embedding path that must mirror the passage convention.

## Options Evaluated (current MTEB, 2026; all 384-dim, all 512-token window except MiniLM)

| Model | Retrieval (15) | Window | Prefix | trust_remote_code | License |
|-------|---------------:|:------:|--------|:-----------------:|---------|
| all-MiniLM-L6-v2 (incumbent) | 42.35 | 256 | none | no | Apache-2.0 |
| gte-small | 49.46 | 512 | none | no | Apache-2.0 |
| **bge-small-en-v1.5** | **51.68** | 512 | query-only, **optional** in v1.5 | no | MIT |
| e5-small-v2 | ~46 | 512 | `query:`/`passage:` (mandatory, both sides) | no | MIT |

## Analysis

Key insights:
- **Training objective beats dimension count.** At identical 384-dim, bge-small-en-v1.5 outscores MiniLM by ~+9 retrieval points and gte-small by ~+2. A corroborating real-corpus test (DEV community) had bge-small win top-1 on 4/5 queries vs MiniLM and was adopted wholesale.
- **The 512-token window is a second, independent win** that matters specifically for *this* corpus: median message is tiny (167 chars) but the tail runs to 202 KB. A 512 window (vs MiniLM's 256) lets chunks be ~2× larger, which — combined with the per-chunk storage decision — means fewer chunk rows, less per-chunk truncation risk, and tighter chunk semantics.
- **Prefix coordination** is the one ergonomic wrinkle. e5 mandates `query:`/`passage:` on *both* sides (most error-prone). bge-small-en-v1.5 needs **no passage prefix ever**, and its *query* prefix is **optional** (v1.5 explicitly: "slight degradation" without it). gte-small needs none at all. So m1 (passages) is prefix-free for both bge and gte; only m2's query path optionally differs.
- **Supply chain**: bge-small-en-v1.5 and gte-small are plain BERT encoders — **no `trust_remote_code`** (unlike gte-*-v1.5/Qwen2, which execute custom RoPE/pooling code on load — a posture red flag we avoid). bge is MIT.
- **Throughput**: ~33M params (bge/gte) vs 22M (MiniLM) — same CPU-friendly class; first-embed of ~48 K chunks stays in seconds-to-low-minutes on a CPU box. Negligible vs the quality gain.

## Decision

**Selected**: **`bge-small-en-v1.5`** as the m1 default `EMBED_MODEL`.

**Rationale**: Best retrieval at the fixed 384-dim width (no schema change), with a 512-token window that directly helps this corpus's long tail; no `trust_remote_code`; MIT; and m1's passage side needs **no** prefix, so the cross-milestone contract stays simple (m2 may optionally add the query instruction for a small gain). It wins on the top three ranked attributes simultaneously and ties the incumbent on CPU-friendliness.

**Tradeoff**: ~50% more parameters than MiniLM (still tiny) and a different one-time model download (~130 MB) to provision/cache (same mechanism as the torch/vss provisioning the project already accepts). Accepted.

## Empirical Update (2026-06-28 spike — `planning/spikes/embed-model-eval/`)

The desk pick was tested on the operator's real corpus (known-item retrieval:
user turn → its assistant reply, 2,110 pairs vs 14,472 distractors; torch
provisioned locally on a GTX 1070). Headline (MRR@10 / R@1 / CPU-per-s):

| model | MRR@10 | R@1 | CPU/s | note |
|-------|-------:|----:|------:|------|
| e5-small-v2 | **0.266** | **0.216** | 10 | best top-1; mandatory dual `passage:`/`query:` prefix |
| gte-small | 0.245 | 0.174 | **1** | best median rank but **disqualified** by CPU throughput |
| bge-small-en-v1.5 (query prefix) | 0.239 | 0.178 | 11 | desk pick; no passage prefix; MIT |
| bge-small-en-v1.5 (no prefix) | 0.204 | 0.151 | 8 | prefix is worth +0.035 MRR |
| all-MiniLM-L6-v2 | 0.192 | 0.137 | 23 | incumbent — clearly weakest quality |

Confirmations: switching off MiniLM is justified; the bge **query prefix matters**
(use it in m2). Surprise: **e5-small-v2 beats the MTEB ordering on this corpus**
(top R@1/MRR) — so the finalists were **e5-small-v2** (peak top-1, fast, dual-prefix
contract spanning m1+m2) vs **bge-small-en-v1.5+prefix** (simpler/lower-footgun
contract for a hair less R@1).

**Cross-corpus validation (2026-06-29):** the benchmark was re-run on a second,
independent corpus — a MacBook's Cursor/Claude history (15,775 passages / 2,185
pairs, Apple-Silicon MPS). **The model ordering came out identical**
(`e5 > gte > bge+prefix > bge no-prefix > MiniLM`), confirming the ranking is not
a one-corpus artifact.

**DECISION (RESOLVED — operator): `bge-small-en-v1.5`** stays the m1 model — e5's
small, consistent top-1 edge doesn't outweigh bge's simpler/robust prefix contract
(no passage prefix; m2 query-prefix optional, its gain captured). Escape hatch:
switching to e5 later is a one-line `EMBED_MODEL` + dual prefixes, no schema change
(still 384-dim). See the spike README for both corpora's tables, method, caveats.

## Implementation Notes

- `EMBED_MODEL = "BAAI/bge-small-en-v1.5"`, `EMBED_DIM = 384` (unchanged). `embed_model` is recorded per row, so a future model swap is incremental (re-embed selects rows lacking the *current* model).
- **No `uv.lock` change** — the model is a `sentence_transformers` weight name resolved at runtime, not a Python dependency. No `trust_remote_code`.
- **Passage embedding (m1): no prefix.** Encode `messages.text` chunks raw.
- **Query embedding (m2, forward note): the query prefix is optional**; if used, it is `"Represent this sentence for searching relevant passages: "` prepended to the *query only*. m1 and m2 must agree; default to **no prefix** for simplicity unless m2 measures a gain.
- **Provisioning (Phase 4 note)**: `sr-initialize`'s model warm-up should cache `BAAI/bge-small-en-v1.5` (the o9-torch smoke cached `all-MiniLM-L6-v2`; update that to the chosen model so runtime is offline).
- **Empirical confirmation** (optional, build-time): a real nearest-neighbor sanity check on a sample of the operator's own messages requires provisioning torch (absent here by the lock contract). The desk evaluation is high-confidence; an empirical pass can be folded into the first build step if torch is provisioned.
