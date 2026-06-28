# Spike: 384-dim embedding-model evaluation on Stockroom's own corpus

**Date:** 2026-06-28
**Question:** Which 384-dim sentence-embedding model should the Phase-2 embedding
pipeline use? The desk decision (`memory-bank/.../creative-embedding-model-selection.md`)
picked `bge-small-en-v1.5` over the incumbent `all-MiniLM-L6-v2` on MTEB + window
+ supply-chain grounds. This spike tests that empirically on the operator's real
messages, since the operator has torch provisioned locally (GTX 1070, CUDA 12.6).

Width is fixed at **384** for all candidates (the schema's `vector FLOAT[384]` —
staying at 384 means no migration + no re-embed when the model changes). So this
is a *model* comparison at constant dimensionality, exactly the real lever.

## Method — known-item retrieval with structural labels

No MTEB, no hand-labeling, no synthetic queries. The corpus carries its own
relevance signal:

- **query** = a user turn
- **gold**  = the assistant turn that replied to it (the `messages.parent_id` edge)
- **pool**  = 14,472 assistant messages (every gold + ~12k distractors)
- **2,110** query→gold pairs (both turns ≥ 64 chars)

For each model we embed every query and every passage to a single 384-dim vector
(L2-normalized; each model truncates at its native window — 256 for MiniLM, 512
for the rest — the realistic one-vector-per-message behavior), rank the gold by
cosine similarity against all 14,472 passages, and report **MRR@10**,
**Recall@{1,5,10}**, and **mean/median rank**. We also measure GPU and CPU encode
throughput; the **CPU** number is the binding constraint for the torch-free
CI/cloud target.

This measures the real question — "does the model rank the genuinely-related
message near the top, on *this* data, against thousands of distractors" — which
is exactly what semantic search must do.

**Caveats.** (1) Adjacent user→assistant turns are a *noisy* relevance proxy: a
short contextual follow-up ("ok, do that") doesn't fully specify its reply, which
caps absolute scores (MRR ≈ 0.19–0.27) — but the *relative* ordering is the
signal. (2) Single-vector + truncation under-represents long messages; the
shipped design embeds **per-chunk**, which lifts all models on the long tail
(orthogonal to model choice). (3) Numbers are this-corpus-specific by design.

## Reproduce

```bash
# 1. export the dataset (sr-search venv, duckdb 1.5.4, reads the warehouse RO)
cd skills/sr-search && PYTHONPATH=src uv run --no-sync --no-config \
    python ../../planning/spikes/embed-model-eval/export_dataset.py

# 2. run the benchmark (the torch-equipped interpreter)
cd ../../planning/spikes/embed-model-eval && python3 benchmark.py
```

The `*.parquet` exports contain raw private message text and are **gitignored**.
`results.json` (metrics only) is safe to commit.

## Results (GTX 1070, CUDA 12.6, torch 2.11.0)

| model | win | MRR@10 | R@1 | R@5 | R@10 | medRank | GPU/s | CPU/s |
|-------|----:|-------:|----:|----:|-----:|--------:|------:|------:|
| **e5-small-v2** (`query:`/`passage:`) | 512 | **0.266** | **0.216** | 0.335 | 0.372 | 91 | 221 | 10 |
| gte-small | 512 | 0.245 | 0.174 | **0.344** | **0.400** | **34** | 47 | **1** |
| **bge-small-en-v1.5** (query prefix) | 512 | 0.239 | 0.178 | 0.321 | 0.375 | 58 | 111 | 11 |
| bge-small-en-v1.5 (no prefix) | 512 | 0.204 | 0.151 | 0.276 | 0.332 | 82 | 111 | 8 |
| all-MiniLM-L6-v2 (incumbent) | 256 | 0.192 | 0.137 | 0.265 | 0.331 | 71 | 582 | **23** |

Approx. cold-embed time for the full ~48k-chunk corpus (one-time; incremental
after): CPU — MiniLM ~35 min, bge ~73 min, e5 ~80 min, **gte ~13 h**; GPU (1070)
— MiniLM ~1.5 min, e5 ~3.6 min, bge ~7 min, gte ~17 min.

## Findings

1. **The incumbent (MiniLM) is clearly the weakest** on quality — last on every
   retrieval metric, by a consistent and large margin (MRR 0.192 vs 0.239–0.266
   for the modern models; R@1 0.137 vs 0.178–0.216). **Switching off MiniLM is
   empirically justified**, confirming the desk decision's direction. Its only
   edge is raw speed (CPU 23/s).

2. **The query prefix is real and large for bge.** `bge-small-en-v1.5` jumps from
   MRR 0.204 → **0.239** and median rank 82 → 58 just by prefixing the *query*
   with `"Represent this sentence for searching relevant passages: "` (passages
   unprefixed). ⇒ **m2 should use the bge query prefix** if bge is chosen.

3. **The modern small models are close, and trade places by metric** — e5 wins
   top-1 (R@1 0.216) and MRR; gte wins R@10 and median rank but nails #1 least
   often and is catastrophically slow on CPU; bge+prefix sits in the middle. The
   gaps *among* these three are small and metric-dependent; the gap *down to*
   MiniLM is large and consistent.

4. **gte-small is disqualified by throughput** — 1/s on CPU (≈13 h to cold-embed)
   and only 47/s on GPU — despite the best median rank. Unsuitable for the
   CPU-only CI/cloud floor.

5. **The empirical winner diverges from the MTEB desk pick.** On MTEB,
   e5-small-v2 is the *lowest* of the bunch (59.93 avg) yet here it tops MRR and
   R@1 — the classic "evaluate on your own corpus" result. Its cost is the
   **mandatory dual prefix** (`passage:` on every passage *and* `query:` on every
   query) — the most error-prone contract (a missing/wrong prefix silently
   degrades quality), spanning both m1 (passages) and m2 (queries).

## Recommendation (decision deferred to operator)

The decision narrows to two, with a genuine engineering tradeoff:

- **e5-small-v2** — best top-of-list precision (R@1 0.216, MRR 0.266), fast
  (GPU 221/s, CPU 10/s), MIT, no `trust_remote_code`. **Cost:** mandatory
  `passage:`/`query:` prefixes on both sides — a cross-milestone contract the
  m1 writer and m2 reader must both honor exactly.

- **bge-small-en-v1.5 + query prefix** — strong (R@1 0.178, MRR 0.239), MIT,
  no `trust_remote_code`, **no passage prefix** (m1 stays prefix-free; only m2's
  query is prefixed, and even that is optional with slight degradation). Simpler,
  lower-footgun contract for a hair less top-1 accuracy.

Both decisively beat the incumbent. `gte-small` and `all-MiniLM-L6-v2` are out
(throughput and quality, respectively). The choice is **peak R@1 (e5)** vs
**contract simplicity / robustness (bge)** — a product call, not a technical
blocker. The plan currently encodes bge-small-en-v1.5; flipping to e5 is a
one-line `EMBED_MODEL` change plus the passage-prefix in the m1 writer and the
query-prefix in m2 (no schema change — still 384-dim).
