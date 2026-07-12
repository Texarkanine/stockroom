# Torch provisioning and heal

Torch is held out of `uv.lock` on purpose: each machine picks a CPU or CUDA wheel. After a plugin-root move, the engine `.venv` is disposable — locked deps come back from the lockfile, but torch must be restored from a **machine-local hashed freeze** written when the wheel first passed smoke (or when you ran `make torch`).

## Contract

1. **Install** the chosen wheel into the engine venv (`uv pip install torch --no-config --directory <engine> --index <url>`).
2. **Smoke** with `stockroom doctor smoke` (or the `PYTHONPATH=… uv run …` form in `sr-initialize`).
3. **Freeze** only after smoke succeeds: `stockroom torch freeze --index <url> [--app-dir <engine>]`.

Artifacts under stockroom home (`$STOCKROOM_HOME` or `~/.local/share/stockroom`):

| File | Role |
| --- | --- |
| `torch-requirements.txt` | Hashed freeze (`uv pip compile --generate-hashes --emit-index-url`) of `torch==<accepted version>` plus its deps |
| `torch-index` | Sidecar: the https wheel index URL (debug / re-freeze input) |

Heal (`ensure_engine_env` → `ensure_torch`) never floating-installs from the index alone. If torch is missing, it runs:

```bash
uv pip install --no-config --directory <engine> --require-hashes -r <stockroom_home>/torch-requirements.txt
```

Indexes embedded in the freeze (from `--emit-index-url` at compile time) are what resolve pytorch + PyPI deps. The sidecar is not used for heal resolve.

## Writers

- **`sr-initialize`**: install → smoke → freeze (same index URL that passed smoke).
- **`make torch`**: install then `stockroom torch freeze --index $(TORCH_INDEX)`.
- **CLI**: `stockroom torch freeze --index <url> [--app-dir <engine>]` (default app-dir is the running engine).

## Manual freeze

If you already have an importable torch in the engine venv and only need the durable freeze (e.g. legacy index-only home from an earlier stockroom):

```bash
stockroom torch freeze --index https://download.pytorch.org/whl/cpu
# or, before the shim exists:
PYTHONPATH=skills/sr-search/src python3 -m stockroom torch freeze \
  --app-dir skills/sr-search \
  --index https://download.pytorch.org/whl/cpu
```

## Failure remedy

| Symptom | What to do |
| --- | --- |
| Heal soft-fails: no freeze / corrupt freeze | Re-run `sr-initialize` (pick → install → smoke → freeze), or install + smoke + manual freeze above |
| Heal soft-fails: hash mismatch / yanked wheel | Re-pick a working index, reinstall, smoke, freeze again — do not edit hashes by hand |
| Freeze soft-fails: torch not importable | Install torch into the engine venv first, then freeze |
| Freeze soft-fails: compile error / timeout | Check network / index URL; retry; see `uv pip compile` stderr |

## Shared deps with `uv.lock`

The freeze also pins some PyPI transitives of torch (e.g. `filelock`) that appear in `uv.lock`. Heal installs the freeze **after** the torch-safe inexact deps sync. Inexact sync will not strip torch; minor version drift of those shared deps between lock and freeze is acceptable.

## See also

- [Development](development.md) — torch-safe sync / `make torch`
- [Install](../install.md) — local plugin install without `.venv`
- [`sr-initialize`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-initialize/SKILL.md) — guided onboard
