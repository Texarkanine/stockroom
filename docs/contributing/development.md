# Development

This page is day-to-day work **after** your checkout is wired. For enter → verify → exit (rip-it-out, `HARNESS=… make localdev`, clean), see [Local workflow](local-workflow.md).

From the **repo root**, the [`Makefile`](https://github.com/Texarkanine/stockroom/blob/main/Makefile) is the usual entrypoint — it handles the `skills/sr-search/` directory and the `--no-config` / `--no-sync` flags.

**Jump to a surface:** [Prerequisites](#prerequisites) · [Make targets](#make-targets) · [Engine](#engine) · [Torch](#torch) · [Docs site](#docs-site) · [Dashboard](#dashboard) · [Skills](#skills)

## Prerequisites

- A local checkout already on the [Local workflow](local-workflow.md) path (`stockroom` on PATH baked to this tree, skills wired for your harness if you need them).
- [uv](https://docs.astral.sh/uv/) for the engine and docs toolchains.
- **Node 22** for dashboard JS tests and the full `make test` / `make ci` gate (Node’s built-in test runner; no npm packages).

Machine onboarding for a *released* install (torch pick, doctor smoke, schedule, first ingest) is still [`sr-initialize`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-initialize/SKILL.md) — not `make`. Contributors use Make against a checkout they already own.

### Two uv projects

| Project | Path | Purpose |
| --- | --- | --- |
| Engine | `skills/sr-search/` | Runtime + tests; torch held out of lock |
| Docs | repo root | `properdocs` site only (`uv sync --group docs`) |

Do not confuse the root docs stub `pyproject.toml` with the engine — the engine did not move.

## Make targets

```bash
make help
```

| Target | Role |
| --- | --- |
| `sync` | Install deps from the committed lock (torch-free; strips a previously installed torch) |
| `lock` | Regenerate `uv.lock` hermetically |
| `lock-check` | Fail if the lock is stale vs `pyproject.toml` |
| `test` | Node 22 dashboard tests + pytest (runs `sync` first) |
| `test-js` | Dashboard ES-module tests only (`node --test`) |
| `lint` | `ruff check` |
| `format` | `ruff format` |
| `format-check` | `ruff format --check` (no writes) |
| `reuse` | Whole-tree REUSE lint |
| `ci` | Full engine gate (matches CI) |
| `shim` | Bake this checkout onto PATH (owner `dev`; `TAKEOVER=1` / `FORCE=1` as needed — see Local workflow) |
| `torch` | Install torch out-of-band + freeze under stockroom home |
| `docs` | Local docs preview (`properdocs serve`) |
| `docs-build` | Strict docs build (matches docs CI) |
| `local-skills` | Wire checkout skills (`HARNESS=cursor\|claude` required) |
| `local-engine` | Claim shim + `ensure-env` for this checkout |
| `local-dashboard` | Bounce `stockroom dashboard` |
| `localdev` | Compose the three local atoms |
| `localdev-clean` | Undo localdev bits + drop `owner=dev` shim |
| `localdev-status` | Read-only localdev vs shim report |

Localdev atoms are documented in [Local workflow](local-workflow.md). This page focuses on engine / torch / docs / dashboard / skills loops.

## Engine

The Python engine lives under [`skills/sr-search/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-search) as a locked [uv](https://docs.astral.sh/uv/) project (`[tool.uv] package = false` — run-in-place). Everything is pinned through `uv.lock` **except torch**.

With a `dev` shim baked to this checkout, edits under `skills/sr-search/src/` are what `stockroom` runs — no separate install step for Python sources.

### Day-to-day commands

```bash
make sync          # lock-faithful env (strips torch — see Torch)
make lock          # after editing engine pyproject.toml deps
make test          # pytest + test-js
make lint
make format
make ci            # full gate before you push
```

Regenerate the lock hermetically so ambient user config cannot leak in (`uv lock --no-config` via Make).

When you genuinely need to sync without stripping torch:

```bash
uv sync --project skills/sr-search --inexact --no-config
```

Prefer `make sync` + restore torch via heal when you want lock fidelity; use `--inexact` when you must keep an already-installed torch in the venv during dep iteration.

### Ad-hoc invocation

The on-path `stockroom` command (`~/.local/bin/stockroom`) owns the torch-safe run contract and forwards to subcommands (`query`, `semantic`, `ingest`, `embed`, `migrate`, `shim`, `torch`, `doctor`, `schedule`, `dashboard`). Use `stockroom --help` / `stockroom <subcommand> --help`.

```bash
stockroom ingest --full
stockroom ingest --full --verbose
stockroom embed --verbose
stockroom query "SELECT DISTINCT harness FROM sessions"
stockroom doctor smoke
```

Bake or reclaim the shim with `make shim` / `make local-engine` as described in [Local workflow](local-workflow.md). The shim is baked-only and **succeed-or-refuse**: it never guesses an engine location.

<details>
<summary>Bootstrap footnote: invoking the engine without the shim</summary>

The raw incantation the shim owns (`PYTHONPATH` makes the run-in-place package importable):

```bash
PYTHONPATH=skills/sr-search/src uv run --project skills/sr-search --no-sync --no-config python -m stockroom <subcommand>
```

You should only need this to bootstrap (e.g. what `make shim` runs under the hood).

</details>

## Torch

Torch is held out of the lock on purpose so each machine gets a CPU or CUDA wheel that actually works. Operator contract (why, heal, failure remedies): [Torch](../user-guide/troubleshooting/torch.md).

### Restore after sync

`make sync`, `make test`, and `make ci` install from the lock and **strip** a previously installed torch.

To restore the machine’s **accepted** stack from the hashed freeze (do this after sync when you still want the same torch):

```bash
stockroom shim ensure-env
```

Do **not** run `make torch` for a routine restore — that picks `TORCH_INDEX` and **rewrites** the freeze.

### Try a new Torch

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

## Docs site

Human docs live under [`docs/`](https://github.com/Texarkanine/stockroom/tree/main/docs). The repo-root stub `pyproject.toml` is the **docs toolchain only** (`properdocs` + Material); it is not the engine.

```bash
make docs          # properdocs serve (preview)
make docs-build    # strict build — matches docs CI
```

Config: [`properdocs.yaml`](https://github.com/Texarkanine/stockroom/blob/main/properdocs.yaml). Contributing nav order is controlled by [`docs/contributing/.pages`](https://github.com/Texarkanine/stockroom/blob/main/docs/contributing/.pages).

### Publishing

CI builds with `properdocs build --strict` on every PR (`.github/workflows/docs.yaml`). Deploy runs on a published GitHub Release or a manual `workflow_dispatch`.

**One-time operator step:** after the first successful deploy job, set the repo **Settings → Pages → Source** to **GitHub Actions**. The workflow cannot flip that switch. Until Pages is live, readers can use the markdown under `docs/` on GitHub; the README also links there.

## Dashboard

Product behavior and URL: [Dashboard](../user-guide/dashboard.md) (default [http://localhost:58008](http://localhost:58008/)).

### Where the code lives

| Layer | Path |
| --- | --- |
| Front-end | `skills/sr-search/src/stockroom/dashboard/static/` — native ES modules, vendored Chart.js + markdown-it, no bundler / no npm install |
| Server / CLI | `skills/sr-search/src/stockroom/dashboard/` + `stockroom dashboard` |
| JS tests | `skills/sr-search/tests-js/*.test.mjs` via `make test-js` |
| Python tests | `skills/sr-search/tests/test_dashboard_*.py` via `make test` |

### Develop loop

1. Edit static modules or Python dashboard code in the paths above.
2. Bounce the process so it is serving this checkout:

```bash
make local-dashboard
# or:
stockroom dashboard
```

3. Hard-refresh the browser. Session-start hooks are a marketplace concern; under localdev, prefer the CLI bounce ([Local workflow](local-workflow.md)).

4. Run contracts:

```bash
make test-js       # Node 22 required
make test          # JS + pytest (syncs first — restore torch afterward if you need embed)
```

## Skills

Wrapper skills live under [`skills/`](https://github.com/Texarkanine/stockroom/tree/main/skills): `sr-query`, `sr-semantic`, `sr-search`, `sr-dashboard`, `sr-initialize`. Each skill’s agent-facing instructions are `SKILL.md` (plus optional `references/`).

### Edit and reload

- **Edit** the files in the checkout `skills/<name>/` tree.
- **Cursor:** with localdev skills wired, the project mirror under `.cursor/skills/stockroom-local/` follows those files (`HARNESS=cursor make local-skills`). Reload the window if the harness caches skill text.
- **Claude Code:** load the plugin tree with `claude --plugin-dir /path/to/stockroom` (see [Local workflow](local-workflow.md)); no Cursor-style skills mirror.

Do not commit the Cursor mirror — localdev installs a pre-commit guard so it stays out of git.

### Hygiene

Wrapper skills must invoke the engine only as `stockroom <subcommand>`. They must not carry the pre-shim `PYTHONPATH` / `uv run` incantation. That contract is enforced by `skills/sr-search/tests/test_skill_hygiene.py`.

Licensing for skill prompts is the narrow PPL-S carveout — see [Licensing](licensing.md).

End-user onboarding judgement stays in `sr-initialize`; do not turn Make recipes into a second install manual inside skill prose.
