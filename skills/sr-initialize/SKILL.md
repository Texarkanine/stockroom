---
name: sr-initialize
description: Set up stockroom on this machine — check prerequisites, provision the per-machine torch build, smoke-test the embedding path, put the `stockroom` command on PATH, schedule the nightly ingest+embed, and run the first full ingest. Run this on a new machine, after a "run sr-initialize" error from a sibling skill, or any time the setup seems broken; it re-probes and only does what is still missing.
enable-model-invocation: true
---

# sr-initialize

`sr-initialize` walks a machine from "plugin installed" to "warehouse ready": prerequisites checked, the per-machine torch wheel provisioned and smoke-tested, the on-path `stockroom` command bound, nightly freshness scheduled, and a first full ingest + embed completed. You (the agent) orchestrate; every mechanical check runs through the tested engine CLI (`stockroom doctor`, `stockroom shim`, `stockroom schedule`), and the judgment calls — which torch wheel, whether to take over a working foreign shim, whether (and when) to schedule the nightly job — always go to the user.

**Idempotent by design: the environment is the state.** There is no progress file. Re-running this skill re-probes and skips whatever is already green — torch present → skip provisioning and go to the smoke test; shim live and maintained by its owner → nothing to do; `stockroom schedule status` says installed → skip scheduling; warehouse already populated → skip the first run. "Go install torch your own way and run me again" is a supported flow, not a dead end.

## Step 1: Prerequisite — uv

```bash
command -v uv
```

If missing, stop and tell the user to install [uv](https://docs.astral.sh/uv/getting-started/installation/) first; nothing below works without it.

## Step 2: Find the engine and the shim owner

The engine always sits beside this skill: `sr-search` is this skill's sibling directory in every layout, because the committed layout is the install layout. The owner label goes into the on-path shim and decides who keeps it current:

- **`claude` or `cursor`**: a marketplace install in that harness's default plugins folder, meaning its own copy under `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` or `~/.cursor/plugins/cache/…`, or a Claude Code copy synced from claude.ai under `~/.claude/plugins/synced/…`. A Claude Code install in a custom plugins folder (set by `CLAUDE_CONFIG_DIR` or `CLAUDE_CODE_PLUGIN_CACHE_DIR`) also counts when Claude Code's install record, `installed_plugins.json` beside its `cache` folder, lists it. So does a Cursor install in a custom folder when Cursor exports its plugin root. That harness's session hooks re-bake the shim after plugin updates.
- **`dev`**: anything run from a checkout, such as `claude --plugin-dir`, Cursor's `~/.cursor/plugins/local/`, a local-path marketplace, or the `make localdev` mirror. Contributors manage that shim with `make shim` / `make localdev`.

Run this block as written. Claude Code writes this skill's directory into it when it loads the skill. In any other harness, replace the angle-bracket placeholder with the POSIX absolute path of the directory you read this SKILL.md from (on WSL, turn backslashes into forward slashes). Do not look for plugin-root environment variables yourself: harnesses give them to hooks, not to agent shells.

```bash
SKILL_DIR="${CLAUDE_SKILL_DIR}"
[ -n "$SKILL_DIR" ] || SKILL_DIR="<POSIX absolute path of the directory holding this SKILL.md>"
APP_DIR="$(CDPATH='' cd -- "$SKILL_DIR/../sr-search" 2>/dev/null && pwd)"
PLUGIN_ROOT="${APP_DIR%/skills/sr-search}"
CACHE_DIR="${PLUGIN_ROOT%/*/*/*}"
REAL_APP="$(CDPATH='' cd -P -- "$APP_DIR" 2>/dev/null && pwd)"
CURSOR_APP=""
[ -z "${CURSOR_PLUGIN_ROOT}" ] || CURSOR_APP="$(CDPATH='' cd -P -- "${CURSOR_PLUGIN_ROOT}/skills/sr-search" 2>/dev/null && pwd)"
OWNER=""
if [ ! -f "$APP_DIR/pyproject.toml" ]; then
  printf 'sr-initialize: no stockroom engine beside %s\n' "$SKILL_DIR" >&2
  APP_DIR=""
elif [ "$PLUGIN_ROOT" != "$APP_DIR" ] && [ "${CACHE_DIR##*/}" = cache ]; then
  case "$APP_DIR" in
    */.claude/plugins/cache/*) OWNER=claude ;;
    */.cursor/plugins/cache/*) OWNER=cursor ;;
    *)
      if grep -qF -- "\"$PLUGIN_ROOT\"" "${CACHE_DIR%/*}/installed_plugins.json" 2>/dev/null; then OWNER=claude
      elif [ -n "$CURSOR_APP" ] && [ "$CURSOR_APP" = "$REAL_APP" ]; then OWNER=cursor
      else printf 'sr-initialize: %s is laid out like an installed plugin, but outside the default plugins folders and no install record lists it\n' "$APP_DIR" >&2
      fi ;;
  esac
else
  case "$APP_DIR" in
    */.claude/plugins/synced/*) OWNER=claude ;;
    *) OWNER=dev ;;
  esac
fi
printf "APP_DIR='%s'; OWNER='%s'\n" "$(printf '%s' "$APP_DIR" | sed "s/'/'\\\\''/g")" "$OWNER"
```

It prints one line, such as `APP_DIR='/…/skills/sr-search'; OWNER='claude'`. Shell variables do not carry from one command to the next, so **start every later command in this skill with that printed line**. Copy it exactly: it is already quoted for the shell.

- **`APP_DIR` is empty:** no engine sits beside the directory you used. Fix the directory and run the block again. Do not go on without an engine.
- **`OWNER` is empty but `APP_DIR` is set:** the engine is laid out like an installed plugin, but outside the default plugins folders, and no install record lists it.
  - **In Claude Code:** `claude --plugin-dir` makes a checkout look the same as an unrecorded install here, so ask the user whether `APP_DIR` is a checkout they develop in (`dev`) or a plugin installed in a custom plugins folder (`claude`). Set `OWNER` in the printed line to their answer. Never pick it yourself.
  - **In any other harness:** in the printed line, set `OWNER` to the harness you are running in (for example `cursor`).
- **`OWNER` is `dev`:** everything below works the same, except Step 7, which leaves the shim to the contributor flow.

## Step 3: Sync the locked environment — before torch

```bash
PYTHONPATH="$APP_DIR/src" python3 -m stockroom shim ensure-env --app-dir "$APP_DIR"
```

This is the tested env-heal path (`stockroom.engine_env`): probe with `uv sync --frozen --inexact --check`, and when incomplete run `uv sync --frozen --inexact`. It never exact-syncs, so it is safe whether or not torch is already present. Session/workspace hooks call the same logic via `shim rectify` after a plugin-root move.

**Ordering still matters for torch.** Provision torch only after locked deps exist (steps 4–5). After torch is installed, never run an exact `uv sync` yourself — use `--inexact` / `uv run --no-sync` (see `docs/contributing/iteration/index.md`).

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

For the guided path, install the confirmed wheel (out of band, per the torch contract — note `--no-config` and `--directory`, both required), then verify through the production path — `smoke` prints the torch version and CUDA availability, then encodes one real string through the actual embedding encoder:

```bash
uv pip install torch --no-config --directory "$APP_DIR" \
  --index https://download.pytorch.org/whl/cu126   # ← the user's confirmed build

PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom doctor smoke
```

The first run downloads the embedding model (network needed once); that also pre-warms the cache so the first real embed won't pay it. Exit 0 ends with `ok: encoded one string to a 384-dim vector`.

**On failure, smoke exits 1 with one stderr line that names the next action — relay it and follow it.** The common shape is a wrong wheel (a CUDA kernel error or crash from the encode): go back to step 5, pick a different index (usually an older `cu*` build, or `cpu` as the always-works fallback), reinstall, and re-run the smoke. `uv pip install` replaces the previous build in place.

**Only after smoke succeeds**, freeze the accepted torch stack so plugin updates can reinstall the *same* bits (hashed requirements under stockroom home — see [`docs/user-guide/troubleshooting/torch.md`](../../docs/user-guide/troubleshooting/torch.md)):

```bash
PYTHONPATH="$APP_DIR/src" python3 -m stockroom torch freeze \
  --app-dir "$APP_DIR" \
  --index https://download.pytorch.org/whl/cu126   # ← same URL that passed smoke
```

The freeze lives under stockroom home (`$STOCKROOM_HOME` or `~/.local/share/stockroom/torch-requirements.txt`, plus a `torch-index` sidecar), outside the disposable plugin tree. Session/workspace hooks call `shim rectify` → `ensure_engine_env`, which restores torch from this freeze (`uv pip install --require-hashes -r …`) after a plugin-root move. Do **not** freeze a build that failed smoke.

## Step 7: Bind the `stockroom` command

The shim lives at `~/.local/bin/stockroom`. Read the one that is there now straight from that path, because `~/.local/bin` may not be on PATH yet:

```bash
grep '^# STOCKROOM_' ~/.local/bin/stockroom 2>/dev/null
```

`STOCKROOM_OWNER` is who maintains it, and `STOCKROOM_APP_DIR` is the engine it runs. Check that engine with `LC_ALL=C ls -dL -- "<STOCKROOM_APP_DIR>/pyproject.toml"`, putting in the header's value. It is **alive** when `ls` lists the file. It is **dead** when `ls` fails with "No such file or directory", "Not a directory" or "Too many levels of symbolic links". Any other failure, such as "Permission denied", means it **cannot be checked**. Then:

| What is there | What to do |
| --- | --- |
| No file, or `STOCKROOM_OWNER` equals `OWNER` | Install, below. |
| A file with no `STOCKROOM_` lines | Not a stockroom shim. Tell the user what is at that path. Replace it (`--takeover`) only with their explicit consent. |
| Another owner, engine dead | It can run nothing. Install with `--takeover`, and tell the user what it pointed at. The next harness session would replace it anyway. |
| Another owner, engine cannot be checked | Neither this skill nor the session hooks can tell whether it still works, so they leave it. Tell the user what it points at and why it cannot be checked. Offer `--takeover --force`, and run it only with their explicit consent. |
| Owner `dev`, engine alive, `STOCKROOM_APP_DIR` inside a marketplace install (`…/cache/<marketplace>/<plugin>/<version>/…`, or a claude.ai-synced copy under `…/.claude/plugins/synced/…`) | An earlier `sr-initialize` probably mislabelled a real install. No harness hook will ever refresh it, and a plugin update can remove that directory. If the path is outside the default plugins folders (`~/.claude/plugins/…`, `~/.cursor/plugins/…`), first ask whether it is a checkout the user develops in; if it is, leave it, as in the next row. Skip that question when the Step 2 block itself printed `OWNER='claude'` or `OWNER='cursor'` for that same path, or the user has just told you it is an install; an owner you filled in yourself does not count. Otherwise explain this and offer `--takeover --force`. Run it only with the user's explicit consent. |
| Another owner, engine alive, anything else | Leave it. Either another harness's hooks keep it current, or a contributor is running a checkout on purpose. Tell the user who maintains it; nothing to do here. |

To install:

- **`OWNER` is `claude` or `cursor`.** Add `--takeover` or `--takeover --force` only where the table says so.

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom shim install --owner "$OWNER" --app-dir "$APP_DIR"
```

- **`OWNER` is `dev`.** Only if `APP_DIR` is in a checkout the user develops in, work from that checkout's root. Installed plugin copies also contain a `Makefile`, so never run these inside one. If this is not the user's checkout, stop and ask.
  - No shim, or a `dev` one: `make shim` (owner `dev`, bakes the checkout).
  - Another owner, engine dead: `make shim TAKEOVER=1`.
  - Another owner, engine cannot be checked: tell the user what it points at, and run `make shim TAKEOVER=1 FORCE=1` only with their explicit consent.
  - Another owner, engine alive: this checkout is not active. If the user wants to develop against it, the contributor guide's `make localdev` flow claims the shim. Run it only at their request.

The install is ownership-guarded and its report is honest — relay it:

- **Refusal** (exit 1, e.g. `…is owned by 'dev' and its engine is alive — refusing to replace a working foreign shim`): relay the line verbatim, then follow the table above. Never add `--takeover` or `--force` on your own judgment beyond what it says.
- **PATH warning** (`…is not on PATH`): the shim wrote fine but won't be found; tell the user to add `~/.local/bin` to their PATH.
- **Success** prints `verified via PATH: stockroom <version>` — the command is live.

From here on, every engine call is `stockroom <subcommand>` (`stockroom --help` lists them).

## Step 8: Schedule nightly freshness

The warehouse stays current by running `stockroom ingest && stockroom embed` every night on the platform's own scheduler — cron on Linux/WSL, launchd on macOS. The engine owns the mechanism; you own the consent. First, re-probe:

```bash
stockroom schedule status
```

`status` reports facts and always exits 0: `installed: <the entry>` or `not installed`, a `daemon: running|not running` liveness fact (cron platforms), and `log: <path>` — where the nightly output goes. **If it says installed, this step is done; skip ahead.**

If not installed, **ask the user** before touching their scheduler: propose installing the nightly job at the default **03:30**, and let them pick a different time if they want one (a machine that is reliably off at 03:30 wants a time it is actually awake for). Then:

```bash
stockroom schedule install                # default 03:30
stockroom schedule install --time 01:15   # or the user's chosen HH:MM
```

Install is idempotent — re-running replaces the previous entry, never duplicates it. On cron it manages only its own marker-delimited block and never touches any other crontab line. The report is honest — relay it:

- **Refusal** (exit 1, `the 'stockroom' command is not on PATH…`): the shim isn't bound yet — go back to step 7, then retry.
- **Warning** (`cron daemon is not running…`): the entry is written but cannot fire; relay the fix verbatim (WSL: `sudo service cron start`, or enable systemd) and make sure the user acts on it — a schedule that can't fire is silent data staleness.
- **Success** prints the installed entry. Sanity-check the fire time is what the user chose.

(`stockroom schedule remove` uninstalls the entry cleanly if the user ever wants it gone.)

## Step 9: First run — populate the warehouse

Don't leave the user waiting until 03:30 for their first data. Run the initial full ingest + embed now, through the shim:

```bash
stockroom ingest --full
stockroom embed
```

Expectations to set: on years of history the ingest takes minutes (it prints per-harness session/message counts when done), and the first `embed` is the long pole — hours are normal for a large corpus on modest hardware. If the smoke test (step 6) didn't already download the embedding model, `embed` pays that one-time download first. Both commands are incremental and idempotent: interrupted or re-run, they resume from what's already done — which is also why the nightly job stays cheap.

Then verify the warehouse answers:

```bash
stockroom query "SELECT (SELECT count(*) FROM sessions) AS sessions, (SELECT count(*) FROM messages) AS messages, (SELECT count(*) FROM embeddings) AS embeddings"
```

Non-zero counts in all three columns means the machine is fully onboarded: engine smoke-tested, `stockroom` on PATH, nightly freshness scheduled, warehouse populated and searchable. Point the user at the `sr-search` skill (or `stockroom query` / `stockroom semantic` directly) and you're done.
