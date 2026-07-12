# Development

From the **repo root**, the [`Makefile`](https://github.com/Texarkanine/stockroom/blob/main/Makefile) is the dev entrypoint — it handles the `skills/sr-search/` cd'ing and the `--no-config` / `--no-sync` flags:

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
make docs          # local docs preview (properdocs serve)
make docs-build    # strict docs build (matches docs CI)
```

**Node 22** is required for the full test gate: `make test` and `make ci` run the dashboard's native ES-module contracts through Node's built-in test runner (no npm packages).

## Two uv projects

| Project | Path | Purpose |
| --- | --- | --- |
| Engine | `skills/sr-search/` | Runtime + tests; torch held out of lock |
| Docs | repo root | `properdocs` site only (`uv sync --group docs`) |

Do not confuse the root docs stub `pyproject.toml` with the engine — the engine did not move.

## Publishing the docs site

CI builds the site with `properdocs build --strict` on every PR (`.github/workflows/docs.yaml`). Deploy runs on a published GitHub Release or a manual `workflow_dispatch`.

**One-time operator step:** after the first successful deploy job, set the repo **Settings → Pages → Source** to **GitHub Actions**. The workflow cannot flip that switch. Until Pages is live, readers can use the markdown under [`docs/`](https://github.com/Texarkanine/stockroom/tree/main/docs) on GitHub; the README also links there.

## The torch-safe run contract

The engine lives inside [`skills/sr-search/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-search) as a locked [uv](https://docs.astral.sh/uv/) project. Everything is pinned and hash-verified through `uv.lock` — **except torch**, which is deliberately held out of the lock and provisioned per-machine (so each box gets the right CPU/CUDA build).

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

`make torch` installs the wheel and freezes the accepted stack under stockroom home so plugin-root heal can replay the same bits (`--require-hashes`). Operator-facing contract (why out of lock, heal, failure remedies): [Torch](../user-guide/torch.md).

### Manual freeze

If you already have an importable torch in the engine venv and only need the durable freeze (e.g. legacy index-only home):

```bash
stockroom torch freeze --index https://download.pytorch.org/whl/cpu
# or, before the shim exists:
PYTHONPATH=skills/sr-search/src python3 -m stockroom torch freeze \
  --app-dir skills/sr-search \
  --index https://download.pytorch.org/whl/cpu
```

### Shared deps with `uv.lock`

The freeze also pins some PyPI transitives of torch (e.g. `filelock`) that appear in `uv.lock`. Heal installs the freeze **after** the torch-safe inexact deps sync. Inexact sync will not strip torch; minor version drift of those shared deps between lock and freeze is acceptable.

## Ad-hoc engine invocation: the `stockroom` command

The on-path `stockroom` command (`~/.local/bin/stockroom`) is how you invoke the engine ad hoc. It is a generated shim that owns the whole torch-safe run contract, and forwards to the dispatcher's subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `torch`, `doctor`, `schedule`, `dashboard`); `stockroom --help` lists them and `stockroom <subcommand> --help` shows each one's own options:

```bash
stockroom ingest --full
stockroom ingest --full --verbose   # mid-run progress (quiet by default)
stockroom embed --verbose           # same for embedding
stockroom query "SELECT DISTINCT harness FROM sessions"
```

Get the shim onto your PATH with `make shim` (bakes this checkout, owner `dev`; plugin installs get theirs from `sr-initialize`). The shim is baked-only and **succeed-or-refuse**: it never guesses at an engine location — if its baked engine dir is gone, or the engine env cannot import locked deps, it refuses with a one-line remedy. Each harness's session/workspace hook runs `shim rectify`, which re-bakes an owned shim after a plugin update **and** ensures the engine uv env (torch-safe inexact sync via `shim ensure-env`, then torch reinstall from the hashed freeze written by `sr-initialize` / `make torch` / `stockroom torch freeze`).

For full machine onboarding — prerequisites, the per-machine torch wheel choice, the `stockroom doctor` smoke test, the shim, the nightly ingest+embed schedule (`stockroom schedule`, cron or launchd), and the first full ingest — run the [`sr-initialize`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-initialize/SKILL.md) skill; it re-probes on every run and only does what is still missing.

## Local plugin load

Use these while iterating on the plugin itself. They are not the supported end-user path — end users follow the [Quickstart](../user-guide/quickstart.md).

### Cursor

```bash
mkdir -p ~/.cursor/plugins/local
# Prefer a real copy; symlinks to a repo outside this tree are often rejected.
rsync -a --delete \
  --exclude .git --exclude .venv --exclude '**/__pycache__' \
  /path/to/stockroom/ ~/.cursor/plugins/local/stockroom/
```

Reload the window (**Developer: Reload Window**). `.cursor-plugin/plugin.json` must sit at `~/.cursor/plugins/local/stockroom/.cursor-plugin/plugin.json`. Excluding `.venv` is intentional — the next `sessionStart` hook runs `shim rectify`, which ensures locked deps and reinstalls torch from the hashed freeze under stockroom home (written by `sr-initialize` / `make torch`). If you never froze a stack, run `sr-initialize` once (or see [Torch](../user-guide/torch.md)).

### Claude Code

```bash
# Session-scoped load from a checkout (no marketplace, no install cache):
claude --plugin-dir /path/to/stockroom
```

For a longer-lived Claude install you still go through a marketplace (local or remote) that lists the plugin.

<details>
<summary>Bootstrap footnote: invoking the engine without the shim</summary>

The raw incantation the shim owns (the engine is run-in-place — `[tool.uv] package = false` — so `stockroom` is not installed on `sys.path`; `PYTHONPATH` makes it importable):

```bash
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom <subcommand>
```

You should only ever need this to bootstrap (e.g. `… python -m stockroom shim install --owner dev --app-dir skills/sr-search`, which is exactly what `make shim` runs).

</details>
