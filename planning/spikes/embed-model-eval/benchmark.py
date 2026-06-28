"""Empirical 384-dim embedding-model benchmark on Stockroom's own corpus.

Run with the torch-equipped interpreter (the one that has torch + sentence-transformers):

    cd planning/spikes/embed-model-eval && python3 benchmark.py

Task — *known-item retrieval* with structural relevance labels:
  query  = a user turn
  gold   = the assistant turn that replied to it (parent_id edge)
  pool   = 14,472 assistant messages (distractors + all gold)
We embed each query and each corpus passage to a single 384-dim vector
(each model truncates at its own token window — a fair, realistic
one-vector-per-message comparison), rank the gold by cosine similarity, and
report MRR@10, Recall@{1,5,10}, and mean/median rank.

Why this is a fair test of the *real* question: it measures, on the operator's
actual conversation text, whether a model puts the genuinely-related message
near the top against ~14.5k distractors — which is exactly what semantic search
must do. It is label-free (no MTEB, no hand annotation), reproducible, and
runs in minutes.

Also measures GPU and CPU encode throughput — the CPU number is the binding
constraint for the torch-free CI/cloud target.
"""

from __future__ import annotations

import json
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

CPU_SAMPLE = 512  # texts used for the CPU-throughput micro-benchmark


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
    gpu_passages_per_s: float
    cpu_passages_per_s: float
    notes: str = ""
    extra: dict = field(default_factory=dict)


def load_dataset() -> tuple[list[str], list[str], np.ndarray, np.ndarray]:
    """Return (corpus_uids, corpus_texts, query_texts, gold_row_indices)."""
    con = duckdb.connect()
    corpus = con.execute(
        f"SELECT uid, text FROM '{HERE / 'corpus.parquet'}'"
    ).fetchall()
    queries = con.execute(
        f"SELECT q_text, gold_uid FROM '{HERE / 'queries.parquet'}'"
    ).fetchall()
    con.close()

    corpus_uids = [r[0] for r in corpus]
    corpus_texts = [r[1] for r in corpus]
    uid_to_row = {uid: i for i, uid in enumerate(corpus_uids)}

    query_texts: list[str] = []
    gold_rows: list[int] = []
    for q_text, gold_uid in queries:
        if gold_uid in uid_to_row:  # guaranteed by export, defensive anyway
            query_texts.append(q_text)
            gold_rows.append(uid_to_row[gold_uid])
    return corpus_uids, corpus_texts, query_texts, np.asarray(gold_rows, dtype=np.int64)


def encode(
    model: SentenceTransformer, texts: list[str], prefix: str, device: str, batch_size: int
) -> tuple[np.ndarray, float]:
    """Encode texts (optionally prefixed); return (unit-normalized vectors, seconds)."""
    payload = [prefix + t for t in texts] if prefix else texts
    if device == "cuda":
        torch.cuda.synchronize()
    start = time.perf_counter()
    vecs = model.encode(
        payload,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        device=device,
    )
    if device == "cuda":
        torch.cuda.synchronize()
    return vecs.astype(np.float32), time.perf_counter() - start


def score(query_vecs: np.ndarray, corpus_vecs: np.ndarray, gold_rows: np.ndarray) -> dict:
    """Rank gold per query by cosine similarity; return retrieval metrics.

    Vectors are unit-normalized, so cosine == dot product. Rank is 1-based:
    the number of corpus items strictly more similar than the gold, plus one.
    """
    q = torch.from_numpy(query_vecs)
    c = torch.from_numpy(corpus_vecs)
    if torch.cuda.is_available():
        q, c = q.cuda(), c.cuda()
    gold = torch.from_numpy(gold_rows).to(q.device)

    ranks = torch.empty(q.shape[0], dtype=torch.int64, device=q.device)
    # Batch the query x corpus matmul to bound memory.
    step = 256
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
    passage_cache: dict,
) -> Result:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n=== {cfg.label}  [{cfg.model_id}] ===", flush=True)
    model = SentenceTransformer(cfg.model_id, device=device)
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
        corpus_vecs, gpu_pps = passage_cache[cache_key]
        print(f"  passages: reused cache ({len(corpus_texts)} vecs)", flush=True)
    else:
        corpus_vecs, secs = encode(model, corpus_texts, cfg.passage_prefix, device, 256)
        gpu_pps = len(corpus_texts) / secs
        passage_cache[cache_key] = (corpus_vecs, gpu_pps)
        print(f"  passages: {len(corpus_texts)} in {secs:.1f}s ({gpu_pps:,.0f}/s on {device})", flush=True)

    query_vecs, _ = encode(model, query_texts, cfg.query_prefix, device, 256)
    metrics = score(query_vecs, corpus_vecs, gold_rows)

    # CPU throughput micro-benchmark (the CI-floor signal).
    model_cpu = model.to("cpu")
    sample = corpus_texts[:CPU_SAMPLE]
    _, cpu_secs = encode(model_cpu, sample, cfg.passage_prefix, "cpu", 32)
    cpu_pps = len(sample) / cpu_secs
    print(
        f"  MRR@10={metrics['mrr10']:.3f}  R@1={metrics['r_at'][1]:.3f} "
        f"R@5={metrics['r_at'][5]:.3f} R@10={metrics['r_at'][10]:.3f} "
        f"median_rank={metrics['median_rank']:.0f}  cpu={cpu_pps:,.0f}/s",
        flush=True,
    )

    del model, model_cpu, query_vecs
    if torch.cuda.is_available():
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
        gpu_passages_per_s=gpu_pps,
        cpu_passages_per_s=cpu_pps,
    )


def main() -> int:
    torch.manual_seed(0)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "n/a"
    print(f"device={device}  gpu={gpu_name}  torch={torch.__version__}  threads={torch.get_num_threads()}")

    corpus_uids, corpus_texts, query_texts, gold_rows = load_dataset()
    print(f"corpus={len(corpus_texts)}  queries={len(query_texts)}")

    passage_cache: dict = {}
    results = [run_config(c, corpus_texts, query_texts, gold_rows, passage_cache) for c in CONFIGS]

    # Summary table (sorted by MRR@10 desc).
    results.sort(key=lambda r: r.mrr10, reverse=True)
    print("\n" + "=" * 100)
    header = f"{'model':36} {'dim':>4} {'win':>4} {'MRR@10':>7} {'R@1':>6} {'R@5':>6} {'R@10':>6} {'medRk':>6} {'gpu/s':>8} {'cpu/s':>7}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.label:36} {r.dim:>4} {r.max_seq_len:>4} {r.mrr10:>7.3f} "
            f"{r.r_at[1]:>6.3f} {r.r_at[5]:>6.3f} {r.r_at[10]:>6.3f} "
            f"{r.median_rank:>6.0f} {r.gpu_passages_per_s:>8,.0f} {r.cpu_passages_per_s:>7,.0f}"
        )

    out = {
        "dataset": {"corpus": len(corpus_texts), "queries": len(query_texts)},
        "device": device,
        "gpu": gpu_name,
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
                "gpu_passages_per_s": r.gpu_passages_per_s,
                "cpu_passages_per_s": r.cpu_passages_per_s,
            }
            for r in results
        ],
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {HERE / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
