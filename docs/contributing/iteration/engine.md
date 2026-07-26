# Engine

The Stockroom Engine is the python code that powers [ingestion](../../user-guide/load/index.md), database migration, and serves the data to the [Dashboard](../../user-guide/dashboard.md).

The Python engine lives under [`skills/sr-search/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-search) as a locked [uv](https://docs.astral.sh/uv/) project (`[tool.uv] package = false` — run-in-place). Everything is pinned through `uv.lock` **except torch**.

## Development Loop

With a `dev` shim baked to this checkout, edits under `skills/sr-search/src/` are what `stockroom` runs — no separate install step for Python sources.

Just edit the python code and try again!

### Changing Dependencies

If you need to change the dependency specification, `uv sync` via `make sync` will remove torch from the venv - it rebuilds the venv just from the lockfile (which Torch, you may recall, is not in).

When you genuinely need to sync without stripping torch:

```bash
uv sync --project skills/sr-search --inexact --no-config
```

Prefer `make sync` + restore torch via `stockroom shim ensure-env` when you want lock fidelity; use `--inexact` when you must keep an already-installed torch in the venv during dep iteration.

!!! tip "Re-Lock When Done!"
	Be sure you use `make lock` to regenerate the lockfile when done.

## Relevant Make Targets

| Target | Role |
| --- | --- |
| `sync` | Install deps from the committed lock (torch-free; strips torch if already installed — see [Torch](#torch)) |
| `lock` | Regenerate `uv.lock` hermetically |
| `lock-check` | Fail if the lock is stale vs `pyproject.toml` |
| `test` | pytest + dashboard JS tests (runs `sync` first) |
| `lint` / `format` / `format-check` | ruff check / format / format --check |
| `reuse` | Whole-tree REUSE lint |
| `ci` | Full engine gate (matches CI) |
| `shim` | Bake this checkout onto PATH (owner `dev`; takeover flags in Local workflow) |
| `local-engine` | Claim shim + `ensure-env` for this checkout |

Engine pytest defaults to process workers via [`pytest-xdist`](https://pytest-xdist.readthedocs.io/) (`addopts = ["-n", "auto"]` in [`skills/sr-search/pyproject.toml`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-search/pyproject.toml)). Make and CI call bare `pytest`, so they inherit that. For serial debugging (or a single flaky case), override with `-n0`:

```bash
cd skills/sr-search && uv run --no-sync --no-config pytest -n0 tests/test_smoke.py -v
```

## Ad-hoc Invocation

The on-path `stockroom` command (`~/.local/bin/stockroom`) owns the torch-safe run contract and forwards to subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `torch`, `doctor`, `schedule`, `dashboard`, `backfill`). Use `stockroom --help` / `stockroom <subcommand> --help`.

A correctly-[prepared](../preparation.md) local checkout will have the `stockroom` CLI on your PATH, pointing at your local checkout's python code. You can use it to run the engine's subcommands directly without having to use a long `uv ...` command.

```bash
stockroom ingest --full
stockroom ingest --full --verbose
stockroom embed --verbose
stockroom query "SELECT DISTINCT harness FROM sessions"
stockroom doctor smoke
```

<details>
<summary>Invoking the engine without the shim</summary>

The raw incantation the shim owns (`PYTHONPATH` makes the run-in-place package importable):

```bash
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom <subcommand>
```

You should never need to do this - doing this is the on-path stockroom CLI's job.

However, you could use this to run the engine from a project that is not wired up for local development, against your actual warehouse/database.

</details>

## Torch

Torch is held out of the lock on purpose so each machine gets a wheel that actually works - there are too many possibilities to try to ship a lockfile with Torch in it that would actually work.

### Relevant Make Targets

| Target | Role |
| --- | --- |
| `torch` | Install torch out-of-band + freeze under stockroom home |
| `sync` / `test` / `ci` | Lock-faithful installs that **strip** a previously installed torch |

### Restore After Sync

After `make sync`, `make test`, or `make ci`, restore the machine's **accepted** stack from the hashed freeze:

```bash
stockroom shim ensure-env
```

Do **not** run `make torch` for a routine restore — that picks `TORCH_INDEX` and **rewrites** the freeze.

### Try a new Torch

When you deliberately want a different wheel or index:

```bash
make torch                                    # CPU wheels (default)
make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126   # CUDA example
stockroom doctor smoke                        # confirm import / embed path
```

`make torch` installs the wheel and freezes the accepted stack under stockroom home so heal can replay it with `--require-hashes`.

## Manual freeze

If torch is already importable in the engine venv and you only need the durable freeze:

```bash
stockroom torch freeze --index https://download.pytorch.org/whl/cpu
# or, before the shim exists:
PYTHONPATH=skills/sr-search/src python3 -m stockroom torch freeze \
	--app-dir skills/sr-search \
	--index https://download.pytorch.org/whl/cpu
```

The freeze also pins some PyPI transitives of torch that appear in `uv.lock`. Heal installs the freeze **after** the torch-safe inexact deps sync. Minor version drift of those shared deps between lock and freeze is acceptable.
