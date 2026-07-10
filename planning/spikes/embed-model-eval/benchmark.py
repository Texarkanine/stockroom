"""Empirical 384-dim embedding-model benchmark on a Stockroom corpus.

Portable across machines/accelerators (CUDA, Apple-Silicon MPS, or CPU). Run
with any interpreter that has torch + sentence-transformers + numpy + duckdb:

    python3 benchmark.py [--label macbook-m4] [--cpu-sample 512]

Task — *known-item retrieval* with structural relevance labels:
  query  = a user turn
  gold   = the assistant turn that replied to it (parent_id edge)
  pool   = every assistant message (distractors + all gold)
We embed each query and each corpus passage to a single 384-dim vector (each
model truncates at its own token window — a fair, realistic
one-vector-per-message comparison), rank the gold by cosine similarity, and
report MRR@10, Recall@{1,5,10}, and mean/median rank.

Why this is a fair test of the *real* question: it measures, on this machine's
actual conversation text, whether a model puts the genuinely-related message
near the top against thousands of distractors — exactly what semantic search
must do. Label-free (no MTEB, no hand annotation), reproducible, runs in minutes.

Also measures accelerator and CPU encode throughput — the CPU number is the
binding constraint for the torch-free CI/cloud target.

PRIVACY: reads the gitignored parquet exports (raw text) but writes only
``results.json`` (metrics + machine/corpus metadata, NO message text). That
file is the only thing intended to leave the machine.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

HERE = Path(__file__).resolve().parent
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@dataclass
class ModelConfig:
    label: str
    model_id: str
    query_prefix: str = ""
    passage_prefix: str = ""


CONFIGS = [
    ModelConfig("all-MiniLM-L6-v2 (incumbent)", "sentence-transformers/all-MiniLM-L6-v2"),
    ModelConfig("bge-small-en-v1.5 (no prefix)", "BAAI/bge-small-en-v1.5"),
    ModelConfig(
        "bge-small-en-v1.5 (query prefix)",
        "BAAI/bge-small-en-v1.5",
        query_prefix=BGE_QUERY_PREFIX,
    ),
    ModelConfig("gte-small", "thenlper/gte-small"),
    ModelConfig(
        "e5-small-v2", "intfloat/e5-small-v2", query_prefix="query: ", passage_prefix="passage: "
    ),
]


def pick_device() -> str:
    """Best available accelerator: CUDA, then Apple-Silicon MPS, then CPU."""
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def sync(device: str) -> None:
    """Block until queued accelerator work is done, so timings are accurate."""
    if device == "cuda":
        torch.cuda.synchronize()
    elif device == "mps":
        torch.mps.synchronize()


def device_name(device: str) -> str:
    if device == "cuda":
        return torch.cuda.get_device_name(0)
    if device == "mps":
        return "Apple MPS"
    return platform.processor() or "cpu"


@dataclass
class Result:
    label: str
    model_id: str
    dim: int
    max_seq_len: int
    mrr10: float
    r_at: dict[int, float]
    mean_rank: float
    median_rank: float
    accel_passages_per_s: float
    cpu_passages_per_s: float
    extra: dict = field(default_factory=dict)


def load_dataset() -> tuple[list[str], list[str], list[str], np.ndarray]:
    """Return (corpus_uids, corpus_texts, query_texts, gold_row_indices)."""
    con = duckdb.connect()
    corpus = con.execute(f"SELECT uid, text FROM '{HERE / 'corpus.parquet'}'").fetchall()
    queries = con.execute(f"SELECT q_text, gold_uid FROM '{HERE / 'queries.parquet'}'").fetchall()
    con.close()

    corpus_uids = [r[0] for r in corpus]
    corpus_texts = [r[1] for r in corpus]
    uid_to_row = {uid: i for i, uid in enumerate(corpus_uids)}

    query_texts: list[str] = []
    gold_rows: list[int] = []
    for q_text, gold_uid in queries:
        if gold_uid in uid_to_row:  # guaranteed by export; defensive anyway
            query_texts.append(q_text)
            gold_rows.append(uid_to_row[gold_uid])
    return corpus_uids, corpus_texts, query_texts, np.asarray(gold_rows, dtype=np.int64)


def encode(
    model: SentenceTransformer, texts: list[str], prefix: str, device: str, batch_size: int
) -> tuple[np.ndarray, float]:
    """Encode texts (optionally prefixed); return (unit-normalized vectors, seconds)."""
    payload = [prefix + t for t in texts] if prefix else texts
    sync(device)
    start = time.perf_counter()
    vecs = model.encode(
        payload,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        device=device,
    )
    sync(device)
    return vecs.astype(np.float32), time.perf_counter() - start


def score(query_vecs: np.ndarray, corpus_vecs: np.ndarray, gold_rows: np.ndarray, device: str) -> dict:
    """Rank gold per query by cosine similarity; return retrieval metrics.

    Vectors are unit-normalized, so cosine == dot product. Rank is 1-based:
    the number of corpus items strictly more similar than the gold, plus one.
    """
    math_device = device if device in ("cuda", "mps") else "cpu"
    q = torch.from_numpy(query_vecs).to(math_device)
    c = torch.from_numpy(corpus_vecs).to(math_device)
    gold = torch.from_numpy(gold_rows).to(math_device)

    ranks = torch.empty(q.shape[0], dtype=torch.int64, device=math_device)
    step = 256  # batch the query x corpus matmul to bound memory
    for i in range(0, q.shape[0], step):
        sims = q[i : i + step] @ c.T  # (b, n_corpus)
        b_gold = gold[i : i + step]
        gold_sim = sims.gather(1, b_gold.unsqueeze(1))  # (b, 1)
        ranks[i : i + step] = (sims > gold_sim).sum(dim=1) + 1
    ranks_np = ranks.cpu().numpy()

    return {
        "mrr10": float(np.mean(np.where(ranks_np <= 10, 1.0 / ranks_np, 0.0))),
        "r_at": {k: float(np.mean(ranks_np <= k)) for k in (1, 5, 10)},
        "mean_rank": float(np.mean(ranks_np)),
        "median_rank": float(np.median(ranks_np)),
    }


def run_config(
    cfg: ModelConfig,
    corpus_texts: list[str],
    query_texts: list[str],
    gold_rows: np.ndarray,
    device: str,
    cpu_sample: int,
    passage_cache: dict,
) -> Result:
    print(f"\n=== {cfg.label}  [{cfg.model_id}] ===", flush=True)
    model = SentenceTransformer(cfg.model_id, device=device)
    try:
        dim = model.get_embedding_dimension()
    except AttributeError:  # older sentence-transformers
        dim = model.get_sentence_embedding_dimension()
    # Pin each model to its native window. Some models (notably gte-small) ship
    # without a sane max_seq_length, leaving the tokenizer sentinel — which makes
    # them attempt to encode untruncated 50k-token monsters and effectively hang.
    # Cap at the model's real window (MiniLM 256, the rest 512) so every model
    # truncates consistently — the realistic single-vector-per-message behavior.
    native_window = 256 if "MiniLM" in cfg.model_id else 512
    model.max_seq_length = min(model.max_seq_length or native_window, native_window)
    max_seq = model.max_seq_length

    cache_key = (cfg.model_id, cfg.passage_prefix)
    if cache_key in passage_cache:
        corpus_vecs, accel_pps = passage_cache[cache_key]
        print(f"  passages: reused cache ({len(corpus_texts)} vecs)", flush=True)
    else:
        corpus_vecs, secs = encode(model, corpus_texts, cfg.passage_prefix, device, 256)
        accel_pps = len(corpus_texts) / secs
        passage_cache[cache_key] = (corpus_vecs, accel_pps)
        print(f"  passages: {len(corpus_texts)} in {secs:.1f}s ({accel_pps:,.0f}/s on {device})", flush=True)

    query_vecs, _ = encode(model, query_texts, cfg.query_prefix, device, 256)
    metrics = score(query_vecs, corpus_vecs, gold_rows, device)

    # CPU throughput micro-benchmark (the CI-floor signal). Skipped if the
    # accelerator already *is* cpu (no second number to gather).
    if device != "cpu" and cpu_sample > 0:
        model_cpu = model.to("cpu")
        sample = corpus_texts[:cpu_sample]
        _, cpu_secs = encode(model_cpu, sample, cfg.passage_prefix, "cpu", 32)
        cpu_pps = len(sample) / cpu_secs
    else:
        cpu_pps = accel_pps if device == "cpu" else 0.0

    print(
        f"  MRR@10={metrics['mrr10']:.3f}  R@1={metrics['r_at'][1]:.3f} "
        f"R@5={metrics['r_at'][5]:.3f} R@10={metrics['r_at'][10]:.3f} "
        f"median_rank={metrics['median_rank']:.0f}  cpu={cpu_pps:,.0f}/s",
        flush=True,
    )

    del model, query_vecs
    if device == "cuda":
        torch.cuda.empty_cache()

    return Result(
        label=cfg.label,
        model_id=cfg.model_id,
        dim=dim,
        max_seq_len=max_seq,
        mrr10=metrics["mrr10"],
        r_at=metrics["r_at"],
        mean_rank=metrics["mean_rank"],
        median_rank=metrics["median_rank"],
        accel_passages_per_s=accel_pps,
        cpu_passages_per_s=cpu_pps,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="", help="free-form tag for this corpus/machine (e.g. macbook-m4)")
    parser.add_argument("--cpu-sample", type=int, default=512, help="texts for the CPU-throughput micro-benchmark (0 to skip)")
    args = parser.parse_args()

    torch.manual_seed(0)
    device = pick_device()
    dev_name = device_name(device)
    print(
        f"label={args.label or '(none)'}  device={device}  accelerator={dev_name}  "
        f"torch={torch.__version__}  threads={torch.get_num_threads()}  "
        f"os={platform.platform()}"
    )

    corpus_uids, corpus_texts, query_texts, gold_rows = load_dataset()
    print(f"corpus={len(corpus_texts)}  queries={len(query_texts)}")
    if len(query_texts) == 0:
        print("error: no query pairs — run export_dataset.py first")
        return 1

    passage_cache: dict = {}
    results = [
        run_config(c, corpus_texts, query_texts, gold_rows, device, args.cpu_sample, passage_cache)
        for c in CONFIGS
    ]

    results.sort(key=lambda r: r.mrr10, reverse=True)
    print("\n" + "=" * 100)
    header = f"{'model':36} {'dim':>4} {'win':>4} {'MRR@10':>7} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'medRk':>6} {'accel/s':>8} {'cpu/s':>7}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.label:36} {r.dim:>4} {r.max_seq_len:>4} {r.mrr10:>7.3f} "
            f"{r.r_at[1]:>6.3f} {r.r_at[5]:>6.3f} {r.r_at[10]:>6.3f} "
            f"{r.median_rank:>6.0f} {r.accel_passages_per_s:>8,.0f} {r.cpu_passages_per_s:>7,.0f}"
        )

    out = {
        "label": args.label,
        "machine": {"device": device, "accelerator": dev_name, "os": platform.platform(), "python": platform.python_version(), "torch": torch.__version__},
        "dataset": {"corpus": len(corpus_texts), "queries": len(query_texts)},
        "results": [
            {
                "label": r.label,
                "model_id": r.model_id,
                "dim": r.dim,
                "max_seq_len": r.max_seq_len,
                "mrr10": r.mrr10,
                "recall": r.r_at,
                "mean_rank": r.mean_rank,
                "median_rank": r.median_rank,
                "accel_passages_per_s": r.accel_passages_per_s,
                "cpu_passages_per_s": r.cpu_passages_per_s,
            }
            for r in results
        ],
    }
    suffix = f"-{args.label}" if args.label else ""
    out_path = HERE / f"results{suffix}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}  (metrics only — safe to share)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
