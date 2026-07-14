# Development Iteration Cycles

This page is day-to-day work **after** your local checkout is wired up. Don't know what that means? Go through the [Preparation](preparation.md) process first!

## Prerequisites

- A local checkout already on the [Preparation](preparation.md) and wired up in your harness of choice.
- [uv](https://docs.astral.sh/uv/) for the engine and docs toolchains.
- **Node 22** for dashboard JS tests and the full `make test` / `make ci` gate

Machine onboarding for a *released* install (torch pick, doctor smoke, schedule, first ingest) is still [`sr-initialize`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-initialize/SKILL.md) — not `make`. Contributors use Make against a checkout they already own, in order to develop and test changes.

## Mental Models

From the **repo root**, the [`Makefile`](https://github.com/Texarkanine/stockroom/blob/main/Makefile) is the usual entrypoint — it handles the `skills/sr-search/` directory and the `--no-config` / `--no-sync` flags. Run `make help` anytime for the full target list; the sections below only name the targets that matter for that surface.

### Two uv projects

| Project | Path | Purpose |
| --- | --- | --- |
| Engine | `skills/sr-search/` | Runtime + tests; torch held out of lock |
| Docs | repo root | `properdocs` site only (`uv sync --group docs`) |

## Engine

The Stockroom Engine is the python code that powers [ingestion](../user-guide/ingestion.md), database migration, and serves the data to the [Dashboard](../user-guide/dashboard.md).

The Python engine lives under [`skills/sr-search/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-search) as a locked [uv](https://docs.astral.sh/uv/) project (`[tool.uv] package = false` — run-in-place). Everything is pinned through `uv.lock` **except torch**.

### Development Loop

With a `dev` shim baked to this checkout, edits under `skills/sr-search/src/` are what `stockroom` runs — no separate install step for Python sources.

Just edit the python code and try again!

#### Changing Dependencies

If you need to change the dependency specification, `uv sync` via `make sync` will remove torch from the venv - it rebuilds the venv just from the lockfile (which Torch, you may recall, is not in).

When you genuinely need to sync without stripping torch:

```bash
uv sync --project skills/sr-search --inexact --no-config
```

Prefer `make sync` + restore torch via `stockroom shim ensure-env` when you want lock fidelity; use `--inexact` when you must keep an already-installed torch in the venv during dep iteration.

!!! tip "Re-Lock When Done!"
	Be sure you use `make lock` to regenerate the lockfile when done.

### Relevant Make Targets

| Target | Role |
| --- | --- |
| `sync` | Install deps from the committed lock (torch-free; strips torch if already installed — see [Torch](#torch)) |
| `lock` | Regenerate `uv.lock` hermetically |
| `lock-check` | Fail if the lock is stale vs `pyproject.toml` |
| `test` | pytest + dashboard JS tests (runs `sync` first) |
| `lint` / `format` / `format-check` | ruff check / format / format --check |
| `reuse` | Whole-tree REUSE lint |
| `ci` | Full engine gate (matches CI) |
| `shim` | Bake this checkout onto PATH (owner `dev`; takeover flags in Local workflow) |
| `local-engine` | Claim shim + `ensure-env` for this checkout |

### Ad-hoc Invocation

The on-path `stockroom` command (`~/.local/bin/stockroom`) owns the torch-safe run contract and forwards to subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `torch`, `doctor`, `schedule`, `dashboard`). Use `stockroom --help` / `stockroom <subcommand> --help`.

A correctly-[prepared](preparation.md) local checkout will have the `stockroom` CLI on your PATH, pointing at your local checkout's python code. You can use it to run the engine's subcommands directly without having to use a long `uv ...` command.

```bash
stockroom ingest --full
stockroom ingest --full --verbose
stockroom embed --verbose
stockroom query "SELECT DISTINCT harness FROM sessions"
stockroom doctor smoke
```

<details>
<summary>Invoking the engine without the shim</summary>

The raw incantation the shim owns (`PYTHONPATH` makes the run-in-place package importable):

```bash
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom <subcommand>
```

You should never need to do this - doing this is the on-path stockroom CLI's job.

However, you could use this to run the engine from a project that is not wired up for local development, against your actual warehouse/database.

</details>

### Torch

Torch is held out of the lock on purpose so each machine gets a wheel that actually works - there are too many possibilities to try to ship a lockfile with Torch in it that would actually work.

#### Relevant Make Targets

| Target | Role |
| --- | --- |
| `torch` | Install torch out-of-band + freeze under stockroom home |
| `sync` / `test` / `ci` | Lock-faithful installs that **strip** a previously installed torch |

#### Restore After Sync

After `make sync`, `make test`, or `make ci`, restore the machine’s **accepted** stack from the hashed freeze:

```bash
stockroom shim ensure-env
```

Do **not** run `make torch` for a routine restore — that picks `TORCH_INDEX` and **rewrites** the freeze.

#### Try a new Torch

When you deliberately want a different wheel or index:

```bash
make torch                                    # CPU wheels (default)
make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126   # CUDA example
stockroom doctor smoke                        # confirm import / embed path
```

`make torch` installs the wheel and freezes the accepted stack under stockroom home so heal can replay it with `--require-hashes`.

### Manual freeze

If torch is already importable in the engine venv and you only need the durable freeze:

```bash
stockroom torch freeze --index https://download.pytorch.org/whl/cpu
# or, before the shim exists:
PYTHONPATH=skills/sr-search/src python3 -m stockroom torch freeze \
	--app-dir skills/sr-search \
	--index https://download.pytorch.org/whl/cpu
```

The freeze also pins some PyPI transitives of torch that appear in `uv.lock`. Heal installs the freeze **after** the torch-safe inexact deps sync. Minor version drift of those shared deps between lock and freeze is acceptable.

## Documentation Site

Human docs live under [`docs/`](https://github.com/Texarkanine/stockroom/tree/main/docs).

The documentation site is built with [properdocs](https://properdocs.org/) (a fork of [mkdocs](https://www.mkdocs.org/)) and Material for MkDocs.

1. Configuration: [`./properdocs.yaml`](https://github.com/Texarkanine/stockroom/blob/main/properdocs.yaml)
2. Content: [`./docs/`](https://github.com/Texarkanine/stockroom/tree/main/docs)
3. Dependencies: [`./pyproject.toml`](https://github.com/Texarkanine/stockroom/blob/main/pyproject.toml)

### Development Loop

1. `make docs` to start the local preview server
	* If you are doing heavy refactoring and causing many broken links, it may be helpful to run in non-strict mode: `uv run properdocs serve --no-strict`. CI will be strict, though.
2. Edit the markdown files in `docs/`

#### Changing Dependencies

The root `pyproject.toml` uses the `docs` dependency group to specify the dependencies for the documentation site.

There's nothing special here; just normal [uv](https://docs.astral.sh/uv/) usage. Once you modify the root `pyproject.toml`'s dependency spec, just run `uv sync --group docs && uv lock`.

### Relevant Make Targets

| Target | Role |
| --- | --- |
| `docs` | Local preview (`properdocs serve`) |
| `docs-build` | Strict build — matches docs CI |

Config: [`properdocs.yaml`](https://github.com/Texarkanine/stockroom/blob/main/properdocs.yaml). Contributing nav order is controlled by [`docs/contributing/.pages`](https://github.com/Texarkanine/stockroom/blob/main/docs/contributing/.pages).

### Publishing

CI builds with `properdocs build --strict` on every PR (`.github/workflows/docs.yaml`). Deploy runs on a published GitHub Release or a manual `workflow_dispatch`.

## Dashboard

Product behavior and URL: [Dashboard](../user-guide/dashboard.md) (default [http://localhost:58008](http://localhost:58008/)).

| Layer | Path |
| --- | --- |
| Front-end | `skills/sr-search/src/stockroom/dashboard/static/` — native ES modules, vendored Chart.js + markdown-it, no bundler / no npm install |
| JS tests | `skills/sr-search/tests-js/*.test.mjs` |
| Server | `skills/sr-search/src/stockroom/dashboard/` |
| CLI | `skills/sr-search/src/stockroom/dashboard/__main__.py` |
| Python tests | `skills/sr-search/tests/test_dashboard_*.py` |

### Development Loop

Static ESM is read from disk on each request; Python changes only get picked up after the dashboard server process is replaced.

1. Edit server/metrics (and any other Python under `dashboard/`) plus the static modules that consume the API.
2. Bounce so this checkout’s Python is what is listening:

	```bash
	make local-dashboard
	```

3. Hard-refresh the browser so cached ESM is not stale.
4. Run the dashboard contract gates:

	```bash
	make test-dashboard-js
	make test-dashboard-py
	```

### Relevant Make targets

| Target | Role |
| --- | --- |
| `test-dashboard-js` | Dashboard ES-module tests (`node --test`; Node 22; no sync) |
| `test-dashboard-py` | `tests/test_dashboard_*.py` only (torch-safe; no sync) |
| `test` | Full pytest + JS (runs `sync` first — strips torch) |
| `local-dashboard` | Bounce `stockroom dashboard` for this checkout |

## Skills

Wrapper skills live under [`skills/`](https://github.com/Texarkanine/stockroom/tree/main/skills): `sr-query`, `sr-semantic`, `sr-search`, `sr-dashboard`, `sr-initialize`. Each skill’s agent-facing instructions are `SKILL.md` (plus optional `references/`).

### Relevant Make targets

| Target | Role |
| --- | --- |
| `local-skills` | Wire checkout skills (`HARNESS` must be `cursor` or `claude`) |
| `localdev` / `localdev-clean` / `localdev-status` | Full enter/clean/status composition — see [Preparation](preparation.md) |

### Edit and reload

- **Edit** the files in the checkout `skills/<name>/` tree.
- **Cursor:** with localdev skills wired, the project mirror under `.cursor/skills/stockroom-local/` follows those files (`HARNESS=cursor make local-skills`). Reload the window if the harness caches skill text.
- **Claude Code:** load the plugin tree with `claude --plugin-dir /path/to/stockroom` (see [Preparation](preparation.md)); no Cursor-style skills mirror.

Do not commit the Cursor mirror — localdev installs a pre-commit guard so it stays out of git.

### Hygiene

Wrapper skills must invoke the engine only as `stockroom <subcommand>`. They must not carry the pre-shim `PYTHONPATH` / `uv run` incantation. That contract is enforced by `skills/sr-search/tests/test_skill_hygiene.py`.

Licensing for skill prompts is the narrow PPL-S carveout — see [Licensing](licensing.md).

End-user onboarding judgement stays in `sr-initialize`; do not turn Make recipes into a second install manual inside skill prose.
