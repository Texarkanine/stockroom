# O9 Spike — Lock Everything Except Torch

Empirical resolution of brainstorm Open Item **O9** (and hard requirement **D6**): can a uv project lock *everything* with a committed, hash-verified lockfile while keeping **torch** out of the cross-platform lock and provisioned per-machine, with `sentence-transformers` still working?

**Answer: yes.** Full write-up lives in `planning/tech-brief.md` → *The Torch Exception*. This directory is the reproducible artifact behind it.

## What's Here

- `pyproject.toml` — representative deps (`duckdb`, `sentence-transformers`, `numpy`); torch excluded from the lock via an impossible-marker override.
- `uv.lock` — the hermetic result: 38 packages, 533 hashes, all from PyPI, **zero torch/CUDA/nvidia entries**.
- `smoke.py` — proves the locked-minus-torch env can load `all-MiniLM-L6-v2` from local cache (offline) and embed once torch is provided.

## Reproduce

```bash
# 1. Lock hermetically (ignore ambient user-level indexes so nothing leaks into the lock)
uv lock --no-config

# 2. Install the locked deps — no torch present; importing sentence_transformers fails here, by design
uv sync --frozen

# 3. Provide torch out-of-band, per-machine. --no-config bypasses the override; --index picks the build.
#    (Use the URL matching your accelerator/driver; cu126 shown for a CUDA box. CPU: .../whl/cpu)
uv pip install torch --no-config --index https://download.pytorch.org/whl/cu126

# 4. Smoke it — runs on GPU if available, else CPU. Use --no-sync so the run never strips torch.
uv run --no-sync --no-config python smoke.py
```

## Load-Bearing Findings

- **Exclude torch from the lock:** `[tool.uv] override-dependencies = ["torch; python_full_version < '3'"]`. The marker is always false (`requires-python` ≥ 3.11), so torch and its CUDA transitives never enter resolution.
- **`uv lock` must use `--no-config`:** otherwise a user-level pytorch index pins ordinary pure-Python packages to `download.pytorch.org` instead of PyPI. A shipped lock can't depend on the build machine's config.
- **`uv pip install torch` needs `--no-config` too:** with the override active it is a no-op ("Audited 1 package", 0 installed).
- **Never run an exact `uv sync` after provisioning torch:** it uninstalls torch (not in the lock). Use `uv run --no-sync`, or `uv sync/run --inexact`, which preserve out-of-lock packages.
- **Torch is a per-machine human choice:** PyPI's default torch (cu130/2.12 at spike time) dropped Pascal `sm_61` and crashes on the GTX 1070 (`no kernel image available`); the cu126/2.11 wheel ships `sm_60` and works. `sr-initialize` must let the user pick the index and smoke-test it.

The `.venv/` is intentionally not committed; step 1–2 regenerate it.
