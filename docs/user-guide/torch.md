# Torch

Torch is held out of `uv.lock` on purpose: each machine picks a CPU or CUDA wheel. After a plugin-root move, the engine `.venv` is disposable — locked deps come back from the lockfile, but torch must be restored from a **machine-local hashed freeze** written when the wheel first passed smoke.

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

On-disk paths: [Installed layout](installed-layout.md).

## Failure remedy

| Symptom | What to do |
| --- | --- |
| Semantic search or embed fails citing torch / environment | Re-run `sr-initialize` (do not retry the query hoping torch appears) |
| Heal soft-fails: no freeze / corrupt freeze | Re-run `sr-initialize` (pick → install → smoke → freeze) |
| Heal soft-fails: hash mismatch / yanked wheel | Re-pick a working index, reinstall, smoke, freeze again — do not edit hashes by hand |
| Freeze soft-fails: torch not importable | Install torch into the engine venv first, then freeze |
| Freeze soft-fails: compile error / timeout | Check network / index URL; retry; see `uv pip compile` stderr |

## See also

- [Quickstart](quickstart.md) — first-time `sr-initialize`
- [Troubleshooting](troubleshooting.md) — broader recovery catalog
- [Development](../contributing/development.md) — `make torch`, torch-safe sync (contributors)
