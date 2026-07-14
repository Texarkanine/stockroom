# Packaging

How Stockroom code arrives on a machine and how it is invoked. Procedures for install, heal steps, and day-to-day Make loops live elsewhere; this page is the shape of the design.

## Entrypoint

The on-path `stockroom` command and the repair surface that keeps it honest. Other docs name these constantly — start here.

### The stockroom shim

The generated on-path command (`~/.local/bin/stockroom`) owns the entire invocation contract: engine-directory resolution, `PYTHONPATH`, and torch-safe uv flags. Every caller that runs Stockroom — skills, session-start hooks, the nightly schedule, humans on the CLI — goes through this entrypoint.

Wrapper skills say only `stockroom <subcommand>`. They carry **no fallback incantation**. If `stockroom` is missing from `PATH`, the machine is not initialized; the correct next action is `sr-initialize` (or the contributor equivalent in [Preparation](../contributing/preparation.md)).

The shim is **baked-only and succeed-or-refuse**. A baked `APP_DIR` is written into the script at install/rectify time. At runtime the shim does not scan, rank, or guess an engine location — it either execs that bake through the torch-safe contract or refuses with a one-line remedy.

Ownership is explicit (`STOCKROOM_OWNER` in the shim header). Only the owner may rewrite an existing shim; foreign takes over require explicit flags (contributor Make paths — not Architecture recipes).

Three writers share one tested surface:

| Writer | Role |
| --- | --- |
| `shim install` | First bake / guarded rewrite (`sr-initialize`, `make shim`) |
| `shim rectify` | Hook-safe heal: create if absent, rebake when owned and drifted, ensure engine env — never touch a foreign owner |
| `shim ensure-env` | Env-only subset when the shim file itself is already correct |

Because the engine is run-in-place (not an installed package), making `stockroom` importable is part of this contract — not something skills invent ad hoc. Layout and lock details: [Engine inside sr-search](#engine-inside-sr-search), [Locked uv project](#locked-uv-project).

### Heal

**Heal** is the repair surface for the packaging/runtime contract: restore a correct on-path shim bake, a usable engine uv environment, and (when needed) torch from the per-machine freeze — without treating every failure as a full re-onboard from scratch.

What heal restores:

- **Shim bake** — missing on-path file, or owned shim whose `APP_DIR` drifted after a plugin path move
- **Engine env** — locked deps present via torch-safe inexact sync (never an exact sync that would strip torch)
- **Torch** — reinstall from the hashed freeze under stockroom home when the env cannot import the accepted stack

Who triggers it:

- **Session-start hooks** — `shim rectify` on every session (fire-and-forget; see [Lifecycle](lifecycle.md#session-start-hooks))
- **`sr-initialize`** — full machine setup *and* the intentional re-run when setup looks broken
- **Explicit `shim ensure-env`** — when the shim file is fine but the env/torch side is not

What heal is **not**:

- Not ingest, embed, or migrate
- Not a second copy of User Guide troubleshooting steps — recipes live in [Quickstart](../user-guide/quickstart.md), [Torch troubleshooting](../user-guide/troubleshooting/torch.md), and [Preparation](../contributing/preparation.md)
- Not “retry the query” — a missing torch or stale bake is an environment problem

Heal and [torch held out of the lock](#torch-held-out-of-the-lock) are one story: the freeze exists so heal can replay a machine-specific wheel that the lockfile cannot name.

## Plugin layout

How the plugin is shaped on disk: dual manifests, where the engine lives, the hermetic lock, and the torch exception to that lock.

### Dual-manifest plugin

Stockroom is one plugin with two manifests: `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`, both over a shared `skills/` tree. The committed repository layout **is** the install layout — what the plugin manager copies to disk is exactly what runs. There is no separate build step that produces the plugin payload.

### Engine inside sr-search

The full Python engine lives under `skills/sr-search/`: `pyproject.toml`, `uv.lock`, `src/stockroom/`, migrations, and tests. Sibling `sr-*` skills have no Python of their own. Skill prose and engine behavior must stay in sync because they ship as one unit — there is no separate download of engine code at runtime.

### Locked uv project

The engine is a locked [uv](https://docs.astral.sh/uv/) project with `[tool.uv] package = false`: run-in-place, no console-script entry points, not installed onto `sys.path` by packaging. Dependencies are pinned through a committed `uv.lock`. Lock hermetically (`uv lock --no-config`); what GitHub shows is what the machine is expected to run.

### Torch held out of the lock

Torch is required for embedding (writing vectors and encoding semantic-search queries) but is **held out of the dependency lock**. The correct torch build is a per-machine choice (CPU, CUDA generation, MPS) that no single lockfile can make. It is provisioned out of band, smoke-tested, and frozen under stockroom home; [heal](#heal) reinstalls from that freeze.

After torch is installed, runs must not do an *exact* dependency sync: an exact sync removes anything not in the lock, including the provisioned torch. Torch-safe paths use inexact sync / `--no-sync` as appropriate.

A missing torch is an environment problem, never a query-phrasing problem. Operational steps: [User Guide → Troubleshooting → Torch](../user-guide/troubleshooting/torch.md); contributor sync loops: [Contributing → Iteration](../contributing/iteration.md).

## Related procedures

- First-time setup and heal recipes: [User Guide → Quickstart](../user-guide/quickstart.md), [Installed layout](../user-guide/installed-layout.md), [Torch troubleshooting](../user-guide/troubleshooting/torch.md)
- Contributor checkout wiring and Make loops: [Contributing → Preparation](../contributing/preparation.md), [Iteration](../contributing/iteration.md)
- Licensing carveouts: [Contributing → Licensing](../contributing/licensing.md)
- Agent-facing compact form of these doctrines: [`system-model.md`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-search/references/system-model.md)
