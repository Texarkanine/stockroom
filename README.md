# stockroom

A local, faithful, searchable warehouse of your agentic-coding history.

Stockroom captures the prompts, responses, and tool inputs from your AI
coding sessions (Cursor and Claude Code) into a single-file
[DuckDB](https://duckdb.org/) warehouse with local
[`sentence-transformers`](https://www.sbert.net/) embeddings, so you can
search across everything you and your agents have ever done. Captured content
is stored **whole** — truncation is a read-time convenience, never a
storage-time loss.

It ships as a **dual-manifest plugin** (one shared `skills/` tree serving both
Cursor and Claude Code) with **no build step**: the committed layout is the
install layout.

> **Status: v1 ship gate met.** Listed in [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins);
> release-please syncs version into both plugin manifests; marketplace install →
> `sr-initialize` → all four surfaces proven on Cursor and Claude Code against
> real history. Known caveat: Cursor `sessionStart` auto-dashboard on some WSL
> hosts — see [#12](https://github.com/Texarkanine/stockroom/issues/12); use
> `/sr-dashboard` or `stockroom dashboard` instead.

## Install

The committed repo **is** the install layout — dual manifests over a shared [`skills/`](skills/) tree, no build or bundle step.

### Marketplace

**Cursor** ([marketplace docs](https://cursor.com/docs/plugins)):

1. Open **Cursor Settings → Plugins**.
2. Paste `https://github.com/Texarkanine/txrk9-agent-plugins` into the search/paste-link box (same flow as [txrk9-agent-plugins](https://github.com/Texarkanine/txrk9-agent-plugins)).
3. Install the `stockroom` plugin from that marketplace.
4. Run first-time setup (`/sr-initialize`).

**Claude Code** ([discover plugins](https://code.claude.com/docs/en/discover-plugins)):

1. Run `/plugin` → **Marketplaces**, or `claude plugin marketplace add Texarkanine/txrk9-agent-plugins`.
2. Install with `/plugin install stockroom@txrk9-agent-plugins` (exact marketplace id may match the catalog `name` field).
3. Run first-time setup (`/stockroom:sr-initialize`).

> Cursor’s “add plugins from folder” UI expects a **marketplace** manifest (`.cursor-plugin/marketplace.json`). Pointing it at this repo fails on purpose — stockroom is a *plugin*, not a marketplace. The catalog lives in `txrk9-agent-plugins`.

### Local / development load (no marketplace)

Use these while iterating, or before the marketplace entry exists. They are **not** the supported end-user path.

**Cursor** ([test plugins locally](https://cursor.com/docs/plugins)):

```bash
mkdir -p ~/.cursor/plugins/local
# Prefer a real copy; symlinks to a repo outside this tree are often rejected.
rsync -a --delete \
  --exclude .git --exclude .venv --exclude '**/__pycache__' \
  /path/to/stockroom/ ~/.cursor/plugins/local/stockroom/
```

Reload the window (**Developer: Reload Window**). `.cursor-plugin/plugin.json` must sit at `~/.cursor/plugins/local/stockroom/.cursor-plugin/plugin.json`.

**Claude Code** ([create plugins](https://code.claude.com/docs/en/plugins)):

```bash
# Session-scoped load from a checkout (no marketplace, no install cache):
claude --plugin-dir /path/to/stockroom
```

For a longer-lived Claude install you still go through a marketplace (local or remote) that lists the plugin — Claude’s permanent install path is marketplace-shaped.

## First-time setup

After the plugin is loaded, run **`sr-initialize`** once (Cursor: `/sr-initialize`; Claude: `/stockroom:sr-initialize`). It checks prerequisites, provisions the per-machine torch wheel, binds the on-path `stockroom` command, offers nightly ingest+embed scheduling, and runs the first full ingest + embed. Re-runs are safe: it re-probes and only does what is still missing.

## Skills and invocation

Invocation forms differ by harness (from [Cursor Plugins](https://cursor.com/docs/plugins) and [Claude Code plugin namespacing](https://code.claude.com/docs/en/plugins)). Engine calls after setup are always `stockroom <subcommand>` on PATH; only the *skill* slash forms below are harness-specific. These forms have been proven against a marketplace install of stockroom on both Cursor and Claude Code.

| Skill | Cursor | Claude Code | Role |
| --- | --- | --- | --- |
| `sr-initialize` | `/sr-initialize` | `/stockroom:sr-initialize` | Machine setup (torch, shim, schedule, first ingest) |
| `sr-search` | `/sr-search` | `/stockroom:sr-search` | Friendly default search (routes to query / semantic) |
| `sr-query` | `/sr-query` | `/stockroom:sr-query` | Read-only SQL against the warehouse |
| `sr-semantic` | `/sr-semantic` | `/stockroom:sr-semantic` | Meaning-based (vector) search |
| `sr-dashboard` | `/sr-dashboard` | `/stockroom:sr-dashboard` | Open the local metrics dashboard |

## Usage after setup

- Prefer **`/sr-search`** (Cursor) or **`/stockroom:sr-search`** (Claude Code) when you are unsure whether the question is structured or meaning-based.
- Use **`/sr-query`** / **`/stockroom:sr-query`** for exact SQL, filters, and counts.
- Use **`/sr-semantic`** / **`/stockroom:sr-semantic`** for recall by meaning.
- Use **`/sr-dashboard`** / **`/stockroom:sr-dashboard`** for the at-a-glance UI (also launched by the session-start hook where the harness PATH is complete; see [#12](https://github.com/Texarkanine/stockroom/issues/12) for Cursor-on-WSL).

## The torch-safe run contract

The engine lives inside [`skills/sr-search/`](skills/sr-search/) as a locked
[uv](https://docs.astral.sh/uv/) project. Everything is pinned and
hash-verified through `uv.lock` — **except torch**, which is deliberately held
out of the lock and provisioned per-machine (so each box gets the right
CPU/CUDA build).

This makes one rule load-bearing: **after torch is installed, never run an
exact `uv sync`** — it would uninstall torch. Always use the inexact forms:

```bash
# Run the engine (preserves out-of-lock torch):
uv run --no-sync python -m stockroom.<entrypoint>

# When you genuinely need to sync (e.g. after editing deps), stay inexact:
uv sync --inexact
```

Regenerate the lock **hermetically** so ambient user config can't leak in:

```bash
make lock          # or: uv lock --no-config  (from skills/sr-search/)
```

The full rationale and the reproducible proof live in
[`planning/spikes/o9-torch/`](planning/spikes/o9-torch/) and the tech brief.

## Development

From the **repo root**, the [`Makefile`](Makefile) is the dev entrypoint — it handles the `skills/sr-search/` cd'ing and the `--no-config` / `--no-sync` flags:

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

**Torch** is held out of the lock on purpose — `make sync` (and anything that depends on it, like `make test`) will remove a previously installed torch. After sync, reinstall with:

```bash
make torch                                    # CPU wheels (default)
make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126   # CUDA example
```

See [`planning/spikes/o9-torch/`](planning/spikes/o9-torch/) for index choices and the full contract.

### Ad-hoc engine invocation: the `stockroom` command

The on-path `stockroom` command (`~/.local/bin/stockroom`) is how you invoke the engine ad hoc. It is a generated shim that owns the whole torch-safe run contract, and forwards to the dispatcher's subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `doctor`, `schedule`); `stockroom --help` lists them and `stockroom <subcommand> --help` shows each one's own options:

```bash
stockroom ingest --full
stockroom query "SELECT DISTINCT harness FROM sessions"
```

Get the shim onto your PATH with `make shim` (bakes this checkout, owner `dev`; plugin installs get theirs from `sr-initialize`). The shim is baked-only and **succeed-or-refuse**: it never guesses at an engine location — if its baked engine dir is gone it refuses with a one-line remedy, and each harness's session-start hook re-bakes its own shim after a plugin update moves the install.

For full machine onboarding — prerequisites, the per-machine torch wheel choice, the `stockroom doctor` smoke test, the shim, the nightly ingest+embed schedule (`stockroom schedule`, cron or launchd), and the first full ingest — run the [`sr-initialize`](skills/sr-initialize/SKILL.md) skill; it re-probes on every run and only does what is still missing.

<details>
<summary>Bootstrap footnote: invoking the engine without the shim</summary>

The raw incantation the shim owns (the engine is run-in-place — `[tool.uv] package = false` — so `stockroom` is not installed on `sys.path`; `PYTHONPATH` makes it importable):

```bash
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom <subcommand>
```

You should only ever need this to bootstrap (e.g. `… python -m stockroom shim install --owner dev --app-dir skills/sr-search`, which is exactly what `make shim` runs).

</details>

## License

Layered, and enforced by `reuse lint` (see [`REUSE.toml`](REUSE.toml)): code is
[AGPL-3.0-or-later](LICENSES/AGPL-3.0-or-later.txt); prompt-shaped skill content
is layered under the Public Prompt License (PPL-S).
