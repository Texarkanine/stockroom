# stockroom

A local, faithful, searchable warehouse of your agentic-coding history.

Stockroom captures the prompts, responses, and tool inputs from your AI
coding sessions (Cursor and Claude Code) into a single-file
[DuckDB](https://duckdb.org/) warehouse with local
[`sentence-transformers`](https://www.sbert.net/) embeddings, so you can
search across everything you and your agents have ever done. Captured content
is stored **whole** — truncation is a read-time convenience, never a
storage-time loss.

It ships as a **dual-manifest plugin** (one shared `skills/` tree serving both
Cursor and Claude Code) with **no build step**: the committed layout is the
install layout.

> **Status: Phase 0 — Foundations.** This repository currently contains the
> substrate (locked Python engine, plugin scaffold, versioning, licensing, and
> the test/lint/format harness). No product behavior ships yet; search lands in
> a later phase.

## The torch-safe run contract

The engine lives inside [`skills/sr-search/`](skills/sr-search/) as a locked
[uv](https://docs.astral.sh/uv/) project. Everything is pinned and
hash-verified through `uv.lock` — **except torch**, which is deliberately held
out of the lock and provisioned per-machine (so each box gets the right
CPU/CUDA build).

This makes one rule load-bearing: **after torch is installed, never run an
exact `uv sync`** — it would uninstall torch. Always use the inexact forms:

```bash
# Run the engine (preserves out-of-lock torch):
uv run --no-sync python -m stockroom.<entrypoint>

# When you genuinely need to sync (e.g. after editing deps), stay inexact:
uv sync --inexact
```

Regenerate the lock **hermetically** so ambient user config can't leak in:

```bash
uv lock --no-config
```

The full rationale and the reproducible proof live in
[`planning/spikes/o9-torch/`](planning/spikes/o9-torch/) and the tech brief.

## Development

The engine's harness runs from `skills/sr-search/`:

```bash
cd skills/sr-search
uv sync --frozen --no-config        # set up the locked, torch-free env
uv run --no-sync pytest             # tests
uv run --no-sync ruff check         # lint
uv run --no-sync ruff format        # format
```

REUSE licensing compliance is checked from the repo root:

```bash
uv run --project skills/sr-search --no-sync reuse lint
```

## License

Layered, and enforced by `reuse lint` (see [`REUSE.toml`](REUSE.toml)): code is
[AGPL-3.0-or-later](LICENSES/AGPL-3.0-or-later.txt); prompt-shaped skill content
is layered under the Public Prompt License (PPL-S).
