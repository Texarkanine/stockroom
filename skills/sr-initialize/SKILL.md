---
name: sr-initialize
description: Set up stockroom on this machine — check prerequisites, provision the per-machine torch build, smoke-test the embedding path, and put the `stockroom` command on PATH. Run this on a new machine, after a "run sr-initialize" error from a sibling skill, or any time the setup seems broken; it re-probes and only does what is still missing.
enable-model-invocation: true
---

# sr-initialize

`sr-initialize` walks a machine from "plugin installed" to "engine ready": prerequisites checked, the per-machine torch wheel provisioned and smoke-tested, and the on-path `stockroom` command bound. You (the agent) orchestrate; every mechanical check runs through the tested engine CLI (`stockroom doctor`, `stockroom shim`), and the two judgment calls — which torch wheel, whether to take over a foreign shim — always go to the user.

**Idempotent by design: the environment is the state.** There is no progress file. Re-running this skill re-probes and skips whatever is already green — torch present → skip provisioning and go to the smoke test; shim present and owned → nothing to do. "Go install torch your own way and run me again" is a supported flow, not a dead end.

## Step 1: Prerequisite — uv

```bash
command -v uv
```

If missing, stop and tell the user to install [uv](https://docs.astral.sh/uv/getting-started/installation/) first; nothing below works without it.

## Step 2: Detect context and resolve the engine dir

Which harness (if any) is running this skill decides the shim owner label; the plugin root decides where the engine lives.

```bash
if [ -n "$CURSOR_PLUGIN_ROOT" ]; then
  OWNER=cursor; APP_DIR="$CURSOR_PLUGIN_ROOT/skills/sr-search"
elif [ -n "$CLAUDE_PLUGIN_ROOT" ]; then
  OWNER=claude; APP_DIR="$CLAUDE_PLUGIN_ROOT/skills/sr-search"
else
  OWNER=dev; APP_DIR="<this skill's own directory>/../sr-search"
fi
```

The sibling-relative fallback works because the committed layout is the install layout — `sr-search` (which hosts the shared engine) always sits beside this skill. Resolve `APP_DIR` to an **absolute** path before using it.

**Neither env var set means you are in a dev checkout** (or a symlinked `make localdev` mirror). Everything below works the same, except the shim step: defer it to `make shim` from the repo root (owner `dev`), unless the user explicitly insists on a harness-owned install.

## Step 3: Sync the locked environment — once, before torch

```bash
[ -d "$APP_DIR/.venv" ] || uv sync --frozen --no-config --directory "$APP_DIR"
```

**Ordering is load-bearing.** This is the one legitimate exact sync, and it is only safe *before* torch exists: torch is deliberately held out of the lock, so an exact sync **removes an installed torch**. That is why the command is guarded on the venv not existing yet — on a re-run, skip it. (After setup, syncs must be `uv sync --inexact`; runs are always `uv run --no-sync`.)

## Step 4: Probe the environment

The engine has no shim yet on a clean machine, so this skill carries the one sanctioned pre-shim invocation (everything after the shim lands uses plain `stockroom …`):

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom doctor probe
```

`probe` is read-only, torch-free, and never fails — it reports facts:

```text
os:              Linux
arch:            x86_64
gpu:             NVIDIA GeForce GTX 1070
driver:          582.28
driver-cuda:     13.0
gpu-compute-cap: 6.1
torch:           not installed
engine-dir:      /home/user/.cursor/plugins/…/skills/sr-search
```

If `torch:` already shows a version, skip straight to the smoke test (step 6).

## Step 5: Choose the torch wheel — recommend, then ask

The wheel is a **per-machine human choice**. Never pick it silently: recommend from the probe facts, explain why, and get the user's confirmation. The index URLs are `https://download.pytorch.org/whl/<build>`:

- **Linux with an NVIDIA GPU**: a `cu*` build at or below the `driver-cuda` ceiling (e.g. `driver-cuda: 13.0` supports `cu126`). **The `sm_` caveat**: the newest wheels drop older GPU generations — check `gpu-compute-cap` against the wheel's supported architectures (e.g. compute cap `6.1` / Pascal is dropped by the newest builds but works on `cu126`). A too-new wheel *installs fine* and then crashes at first kernel launch; the smoke test catches it.
- **macOS, or no GPU** (`gpu: none`): the `cpu` build. (On Apple Silicon the CPU wheel includes MPS support.)
- **Native Windows**: out of scope for v1 — use WSL, which is the Linux path.

**The user may also self-manage torch.** The requirement is only: *torch importable inside the engine environment at `engine-dir`, in any build that passes the smoke test*. A torch installed globally or in another venv does not count — it is invisible to the engine. If they want to install it their own way (now or later), let them; the smoke test is the gate, not the recipe. They can re-run this skill afterwards and it resumes from where the facts say.

## Step 6: Provision and smoke-test

For the guided path, install the confirmed wheel (out of band, per the torch contract — note `--no-config` and `--directory`, both required):

```bash
uv pip install torch --no-config --directory "$APP_DIR" \
  --index https://download.pytorch.org/whl/cu126   # ← the user's confirmed build
```

Then verify through the production path — `smoke` prints the torch version and CUDA availability, then encodes one real string through the actual embedding encoder:

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom doctor smoke
```

The first run downloads the embedding model (network needed once); that also pre-warms the cache so the first real embed won't pay it. Exit 0 ends with `ok: encoded one string to a 384-dim vector`.

**On failure, smoke exits 1 with one stderr line that names the next action — relay it and follow it.** The common shape is a wrong wheel (a CUDA kernel error or crash from the encode): go back to step 5, pick a different index (usually an older `cu*` build, or `cpu` as the always-works fallback), reinstall, and re-run the smoke. `uv pip install` replaces the previous build in place.

## Step 7: Bind the `stockroom` command

If `command -v stockroom` already succeeds and `stockroom --version` answers, the shim is live — nothing to do. Otherwise:

- **Harness context** (`OWNER` is `cursor` or `claude`):

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom shim install --owner "$OWNER"
```

- **Dev checkout**: run `make shim` from the repo root instead (owner `dev`, bakes the checkout).

The install is ownership-guarded and its report is honest — relay it:

- **Refusal** (exit 1, e.g. `…is owned by 'dev' and its engine is alive — refusing to replace a working foreign shim`): relay the line verbatim. A foreign shim with a *dead* engine can be replaced by adding `--takeover` — only with the user's explicit consent, never on your own judgment.
- **PATH warning** (`…is not on PATH`): the shim wrote fine but won't be found; tell the user to add `~/.local/bin` to their PATH.
- **Success** prints `verified via PATH: stockroom <version>` — the command is live.

From here on, every engine call is `stockroom <subcommand>` (`stockroom --help` lists them).

## What's next

Scheduling (nightly ingest + embed) and the first full ingest land in a later milestone of this skill. Until then, populate the warehouse manually when you want it: `stockroom ingest --full`, then `stockroom embed`.
