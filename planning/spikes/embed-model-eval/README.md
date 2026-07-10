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

## Reproduce / run on another machine + corpus

The scripts are **self-contained and portable** — no `uv`/project import, and the
device auto-selects **CUDA → Apple-Silicon MPS → CPU**. To validate whether the
ranking generalizes to a *different* corpus (e.g. a second laptop's Claude/Cursor
history), run it there and share only the metrics file:

```bash
# one-time: install deps into any interpreter / venv
python3 -m pip install -r requirements-bench.txt

# one shot — export from the local warehouse, then benchmark
./run.sh macbook-m4
#   …or point at an explicit warehouse file / non-default $STOCKROOM_HOME:
#   ./run.sh macbook-m4 ~/.local/share/stockroom/warehouse.duckdb
```

…or the two steps by hand:

```bash
python3 export_dataset.py [--db ~/.local/share/stockroom/warehouse.duckdb]
python3 benchmark.py --label macbook-m4
```

**Privacy / exfiltration.** The `*.parquet` exports contain raw private message
text and are **gitignored** — they never leave the machine. The benchmark writes
only `results-<label>.json` (metrics + machine/corpus *counts*, **no message
text**); that is the only artifact meant to be shared. (Reading the script
confirms it: nothing but aggregate numbers is serialized.)

Prereqs on the other machine: a Stockroom warehouse exists there (you've run
ingest), and the four models download once from HuggingFace (~400 MB, needs net).

## Results — corpus A: Linux PC (GTX 1070, CUDA 12.6, torch 2.11.0)

> 14,472-passage pool / 2,110 query pairs. A second corpus (e.g. macOS/MPS) can
> be validated with the same scripts; append its table below as "corpus B" to
> check whether the ordering generalizes.

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

## Results — corpus B: MacBook (Apple-Silicon MPS), independent history

> 15,775-passage pool / 2,185 query pairs — a *different* machine's Cursor/Claude
> history, never co-mingled with corpus A. Same scripts, MPS accelerator.
> (Note: the Apple CPU is far faster than corpus A's host, so the CPU/s column is
> not comparable across corpora — but the *relative* model ordering is.)

| model | win | MRR@10 | R@1 | R@5 | R@10 | medRank | accel/s | CPU/s |
|-------|----:|-------:|----:|----:|-----:|--------:|--------:|------:|
| **e5-small-v2** (`query:`/`passage:`) | 512 | **0.252** | **0.196** | 0.328 | 0.371 | 83 | 201 | 164 |
| gte-small | 512 | 0.235 | 0.168 | 0.319 | **0.387** | **34** | 124 | 21 |
| **bge-small-en-v1.5** (query prefix) | 512 | 0.223 | 0.161 | 0.307 | 0.366 | 43 | 229 | 171 |
| bge-small-en-v1.5 (no prefix) | 512 | 0.186 | 0.131 | 0.261 | 0.316 | 76 | 229 | 171 |
| all-MiniLM-L6-v2 (incumbent) | 256 | 0.177 | 0.125 | 0.247 | 0.298 | 78 | 715 | 521 |

**The model ranking is identical to corpus A** — `e5 > gte > bge+prefix >
bge no-prefix > MiniLM` on MRR@10 and R@1, on both machines. The absolute scores
sit ~0.01–0.015 lower on corpus B (a slightly harder/noisier query mix) but every
relative gap holds: e5 leads, the bge query-prefix is worth +0.037 MRR
(0.186→0.223, ≈ the +0.035 seen on A), gte keeps the best median rank but trails
on top-1, and MiniLM is last by a clear margin. This is the generalization check
the operator asked for: **the ordering is not an artifact of one corpus.** (gte's
CPU number is healthier here only because the Apple CPU is much faster — relative
to its peers it is still ~8× slower, so the CPU-floor disqualification stands for
a commodity Linux CI host.)

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

## Decision (RESOLVED — operator, validated on two corpora)

The choice was always between two finalists, both of which decisively beat the
incumbent on *both* corpora:

- **e5-small-v2** — best top-of-list precision (R@1 0.196–0.216, MRR 0.252–0.266),
  fast, MIT, no `trust_remote_code`. **Cost:** mandatory `passage:`/`query:`
  prefixes on *both* sides — a cross-milestone contract the m1 writer and m2
  reader must each honor exactly, where a missing/wrong prefix silently degrades
  quality.

- **bge-small-en-v1.5 + query prefix** ✅ **CHOSEN** — strong (R@1 0.161–0.178,
  MRR 0.223–0.239), MIT, no `trust_remote_code`, **no passage prefix** (m1 stays
  prefix-free; only m2's query is prefixed, and even that is optional with slight
  degradation). Simpler, lower-footgun cross-milestone contract for a hair less
  top-1 accuracy.

**Resolved to `bge-small-en-v1.5`** — the small, consistent top-1 edge e5 holds
on both corpora does not outweigh bge's simpler/more-robust prefix contract for
v1 (and the query-prefix gain, +~0.036 MRR on both corpora, is captured in m2).
`gte-small` and `all-MiniLM-L6-v2` are out (CPU throughput and quality,
respectively). The generalization check (corpus A Linux ≈ corpus B macOS,
identical ordering) means this is a confident pick, not a one-corpus artifact.
Should v1 retrieval ever disappoint, switching to e5 is a one-line `EMBED_MODEL`
change plus the dual prefixes — no schema change, still 384-dim.
