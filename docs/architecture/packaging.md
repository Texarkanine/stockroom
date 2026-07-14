# Packaging

How Stockroom code arrives on a machine and how it is invoked. Procedures for install, heal, and day-to-day Make loops live elsewhere; this page is the shape of the design.

## Dual-manifest plugin

Stockroom is one plugin with two manifests: `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`, both over a shared `skills/` tree. The committed repository layout **is** the install layout — what the plugin manager copies to disk is exactly what runs. There is no separate build step that produces the plugin payload.

Harness hooks are rendered into harness-specific JSON shapes (`hooks/cursor-hooks.json` vs `hooks/claude-hooks.json`). The event names and nesting differ; do not treat them as interchangeable templates.

## Engine inside sr-search

The full Python engine lives under `skills/sr-search/`: `pyproject.toml`, `uv.lock`, `src/stockroom/`, migrations, and tests. Sibling `sr-*` skills have no Python of their own. Skill prose and engine behavior must stay in sync because they ship as one unit — there is no separate download of engine code at runtime.

## Locked uv project

The engine is a locked [uv](https://docs.astral.sh/uv/) project with `[tool.uv] package = false`: run-in-place, no console-script entry points, not installed onto `sys.path` by packaging. Dependencies are pinned through a committed `uv.lock`. Lock hermetically (`uv lock --no-config`); what GitHub shows is what the machine is expected to run.

Because the engine is not an installed package, making `stockroom` importable is part of the invocation contract the shim owns — not something skills invent ad hoc.

## Torch held out of the lock

Torch is required for embedding (writing vectors and encoding semantic-search queries) but is **held out of the dependency lock**. The correct torch build is a per-machine choice (CPU, CUDA generation, MPS) that no single lockfile can make. It is provisioned out of band, smoke-tested, and frozen under stockroom home; heal paths reinstall from that freeze.

After torch is installed, runs must not do an *exact* dependency sync: an exact sync removes anything not in the lock, including the provisioned torch. Torch-safe paths use inexact sync / `--no-sync` as appropriate.

A missing torch is an environment problem, never a query-phrasing problem. Operational heal steps live in [User Guide → Troubleshooting → Torch](../user-guide/troubleshooting/torch.md); contributor sync loops live in [Contributing → Iteration](../contributing/iteration.md).

## The stockroom shim

The generated on-path command (`~/.local/bin/stockroom`) owns the entire invocation contract: engine-directory resolution, `PYTHONPATH`, and torch-safe uv flags. Wrapper skills say only `stockroom <subcommand>` — they carry **no fallback incantation**. If `stockroom` is missing from `PATH`, the machine is not initialized; the correct next action is `sr-initialize` (or the contributor equivalent in Preparation).

The shim is **baked-only and succeed-or-refuse**. It does not scan or re-resolve the engine at runtime. After a plugin update moves the install directory, session-start hooks run `shim rectify`, which creates a missing on-path shim, re-bakes owned shims, and ensures the engine uv env (torch-safe inexact sync plus torch reinstall from the freeze). `ensure-env` is the env-only subset when the shim file itself is already correct.

## Related procedures

- First-time setup and heal: [User Guide → Quickstart](../user-guide/quickstart.md), [Installed layout](../user-guide/installed-layout.md), [Torch troubleshooting](../user-guide/troubleshooting/torch.md)
- Contributor checkout wiring and Make loops: [Contributing → Preparation](../contributing/preparation.md), [Iteration](../contributing/iteration.md)
- Licensing carveouts: [Contributing → Licensing](../contributing/licensing.md)
- Agent-facing compact form of these doctrines: [`system-model.md`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-search/references/system-model.md)
