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
make lock          # or: uv lock --no-config  (from skills/sr-search/)
```

The full rationale and the reproducible proof live in
[`planning/spikes/o9-torch/`](planning/spikes/o9-torch/) and the tech brief.

## Development

From the **repo root**, the [`Makefile`](Makefile) is the dev entrypoint — it handles the `skills/sr-search/` cd'ing and the `--no-config` / `--no-sync` flags:

```bash
make help          # list targets
make sync          # install from the committed lock (torch-free)
make lock          # regenerate uv.lock hermetically
make lock-check    # fail if the lock is stale vs pyproject.toml
make test          # pytest
make lint          # ruff check
make format        # ruff format
make reuse         # whole-tree reuse lint
make ci            # full gate (matches CI)
```

**Torch** is held out of the lock on purpose — `make sync` (and anything that depends on it, like `make test`) will remove a previously installed torch. After sync, reinstall with:

```bash
make torch                                    # CPU wheels (default)
make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126   # CUDA example
```

See [`planning/spikes/o9-torch/`](planning/spikes/o9-torch/) for index choices and the full contract.

For ad-hoc engine invocations:

```bash
uv run --project skills/sr-search --no-sync --no-config python -m stockroom.<entrypoint>
```

For example, ingest your history and then run raw read-only SQL against the warehouse:

```bash
uv run --project skills/sr-search --no-sync --no-config python -m stockroom.ingest --full
uv run --project skills/sr-search --no-sync --no-config python -m stockroom.query "SELECT DISTINCT harness FROM sessions"
```

## License

Layered, and enforced by `reuse lint` (see [`REUSE.toml`](REUSE.toml)): code is
[AGPL-3.0-or-later](LICENSES/AGPL-3.0-or-later.txt); prompt-shaped skill content
is layered under the Public Prompt License (PPL-S).
