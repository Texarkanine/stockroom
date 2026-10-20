# Torch

[PyTorch](https://pytorch.org/) (“torch”) is the machine-learning library Stockroom uses to turn conversation text into embedding vectors for semantic search. Without it, ingest still works and SQL query still works — meaning-based recall does not.

It is also a pain to ship: the install is large, and the right build depends on *your* machine (CPU-only vs a specific CUDA toolkit - and hey, what's your CPU architecture, by the way?). There is no single wheel that fits every box, and a build from the wrong index will fail in confusing ways.

So Stockroom keeps torch **out of** the locked dependency set on purpose; `uv sync` does not install Torch.

Each machine picks a CPU or CUDA or other wheel once at first install, guided by `sr-initialize`. After a plugin-root move (such as when a new `stockroom` version is published), the engine `.venv` is disposable — locked deps come back from the lockfile. But Torch isn't in the lockfile - it must be restored from a **machine-local hashed freeze** written by that first install.

This ensures that Torch *also* doesn't drift to new versions without your explicit involvement, while still giving you a way to get the Torch that's actually going to work on your machine.

Day-to-day, **`sr-initialize`** owns install → smoke → freeze. Prefer re-running it over hand-editing freeze files.

## Contract

1. **Install** the chosen wheel into the engine venv (`uv pip install torch --no-config --directory <engine> --index <url>`).
2. **Smoke** with `stockroom doctor smoke` (or the form used inside `sr-initialize`).
3. **Freeze** only after smoke succeeds: `stockroom torch freeze --index <url>` (same index URL that passed smoke).

Heal (`ensure_engine_env` → `ensure_torch`) never floating-installs from the index alone. If torch is missing, it runs:

```bash
uv pip install --no-config --directory <engine> --require-hashes -r <stockroom_home>/torch-requirements.txt
```

Indexes embedded in the freeze (from `--emit-index-url` at compile time) resolve pytorch + PyPI deps. The `torch-index` sidecar is for debug / re-freeze input — not heal resolve.

## Failure remedies

### Semantic search or embed fails on torch

When torch cannot be imported and a usable hashed freeze already exists, `stockroom semantic` and `stockroom embed` restore it themselves. They print `restoring torch from the hashed freeze`, install from that freeze, and retry once. Wait for that to finish. A large wheel can take minutes.

If the restore fails, if there is no usable freeze, or if the encoder fails for another reason, the command prints the failure and tells you to re-run `sr-initialize` (install, smoke, then freeze). Do not retry the query.

### Heal soft-fails: no freeze / corrupt freeze

Re-run `sr-initialize` (pick → install → smoke → freeze).

### Heal soft-fails: hash mismatch / yanked wheel

Re-pick a working index, reinstall, smoke, freeze again — do not edit hashes by hand.

### Freeze soft-fails: torch not importable

Install torch into the engine venv first, then freeze.

### Freeze soft-fails: compile error / timeout

Check network / index URL; retry; see `uv pip compile` stderr.

### `stockroom doctor smoke` fails with missing torch

If a hashed freeze already exists under stockroom home, the diagnosis names `stockroom shim ensure-env` and does not install it. If there is no freeze yet, follow `sr-initialize` (install → smoke → freeze).
