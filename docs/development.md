# Development

From the **repo root**, the [`Makefile`](../Makefile) is the dev entrypoint — it handles the `skills/sr-search/` cd'ing and the `--no-config` / `--no-sync` flags:

```bash
make help          # list targets
make sync          # install from the committed lock (torch-free)
make lock          # regenerate uv.lock hermetically
make lock-check    # fail if the lock is stale vs pyproject.toml
make test          # Node 22 dashboard tests + pytest
make test-js       # Node 22 built-in tests only (`node --test`)
make lint          # ruff check
make format        # ruff format
make reuse         # whole-tree reuse lint
make ci            # full gate (matches CI)
make shim          # install the on-path stockroom shim baking this checkout
```

**Node 22** is required for the full test gate: `make test` and `make ci` run the dashboard's native ES-module contracts through Node's built-in test runner (no npm packages).

## The torch-safe run contract

The engine lives inside [`skills/sr-search/`](../skills/sr-search/) as a locked [uv](https://docs.astral.sh/uv/) project. Everything is pinned and hash-verified through `uv.lock` — **except torch**, which is deliberately held out of the lock and provisioned per-machine (so each box gets the right CPU/CUDA build).

After torch is installed, never run an exact `uv sync` — it would uninstall torch. Always use the inexact forms:

```bash
# Run the engine from repo root (preserves out-of-lock torch):
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom.<entrypoint>

# When you genuinely need to sync (e.g. after editing deps), stay inexact:
uv sync --project skills/sr-search --inexact
```

Regenerate the lock **hermetically** so ambient user config can't leak in:

```bash
make lock          # or: uv lock --no-config  (from skills/sr-search/)
```

**Torch** is held out of the lock on purpose — `make sync` (and anything that depends on it, like `make test`) will remove a previously installed torch. After sync, reinstall with:

```bash
make torch                                    # CPU wheels (default)
make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126   # CUDA example
```

`make torch` installs the wheel and freezes the accepted stack under stockroom home so plugin-root heal can replay the same bits (`--require-hashes`). Details: [`docs/torch.md`](torch.md).

## Ad-hoc engine invocation: the `stockroom` command

The on-path `stockroom` command (`~/.local/bin/stockroom`) is how you invoke the engine ad hoc. It is a generated shim that owns the whole torch-safe run contract, and forwards to the dispatcher's subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `torch`, `doctor`, `schedule`, `dashboard`); `stockroom --help` lists them and `stockroom <subcommand> --help` shows each one's own options:

```bash
stockroom ingest --full
stockroom ingest --full --verbose   # mid-run progress (quiet by default)
stockroom embed --verbose           # same for embedding
stockroom query "SELECT DISTINCT harness FROM sessions"
```

Get the shim onto your PATH with `make shim` (bakes this checkout, owner `dev`; plugin installs get theirs from `sr-initialize`). The shim is baked-only and **succeed-or-refuse**: it never guesses at an engine location — if its baked engine dir is gone, or the engine env cannot import locked deps, it refuses with a one-line remedy. Each harness's session/workspace hook runs `shim rectify`, which re-bakes an owned shim after a plugin update **and** ensures the engine uv env (torch-safe inexact sync via `shim ensure-env`, then torch reinstall from the hashed freeze written by `sr-initialize` / `make torch` / `stockroom torch freeze`).

For full machine onboarding — prerequisites, the per-machine torch wheel choice, the `stockroom doctor` smoke test, the shim, the nightly ingest+embed schedule (`stockroom schedule`, cron or launchd), and the first full ingest — run the [`sr-initialize`](../skills/sr-initialize/SKILL.md) skill; it re-probes on every run and only does what is still missing.

<details>
<summary>Bootstrap footnote: invoking the engine without the shim</summary>

The raw incantation the shim owns (the engine is run-in-place — `[tool.uv] package = false` — so `stockroom` is not installed on `sys.path`; `PYTHONPATH` makes it importable):

```bash
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom <subcommand>
```

You should only ever need this to bootstrap (e.g. `… python -m stockroom shim install --owner dev --app-dir skills/sr-search`, which is exactly what `make shim` runs).

</details>
