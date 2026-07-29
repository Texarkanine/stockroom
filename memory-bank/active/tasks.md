# Current Task: fix-cli-version-release-please-sync

**Complexity:** Level 1

## Fix

**What broke:** `stockroom --version` / shim `STOCKROOM_GENERATOR_VERSION` stuck at `0.1.2` while plugin manifests and `.release-please-manifest.json` were at `0.18.0`.

**Why:** `#21` added `__init__.py` as a release-please `generic` extra-file and hand-set `0.1.2`, but the `__version__` line had no `x-release-please-version` marker, so the generic updater never touched it. Packaging lockstep tests did not include `stockroom.__version__`.

**What changed:**
- `skills/sr-search/src/stockroom/__init__.py` — bump to `0.18.0` + `# x-release-please-version`
- `skills/sr-search/tests/test_packaging.py` — lockstep includes `__version__`; marker test; generic path assertion

**Session-start / rectify finding (no code change needed):**
- `stockroom --version` is **live** from `APP_DIR`’s `__version__` (shim execs `python -m stockroom`); plugin update alone updates CLI version once `__version__` is correct — rebake not required for `--version`.
- Baked `STOCKROOM_GENERATOR_VERSION` **is** refreshed by session-start `shim rectify` when the shim is **owned by that harness** and rendered content drifts (version stamp is part of render) → rebake.
- Foreign owner (e.g. `dev` checkout shim while Cursor/Claude hooks rectify) → **noop**; use `make shim` for localdev.
