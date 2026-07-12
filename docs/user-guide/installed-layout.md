# Installed layout

The committed repo is the install layout — dual manifests (`.cursor-plugin/` and `.claude-plugin/`) over a shared `skills/` tree, with no build or bundle step for the plugin payload. What you install from the marketplace is what you see on GitHub.

For the get-running ritual (marketplace → `sr-initialize`), see [Quickstart](quickstart.md). Do not treat `make` / `uv` from a git clone as an alternate onboarding path; those are for contributors (see [Development](../contributing/development.md)).

## Plugin payload

| Path | Role |
| --- | --- |
| `.cursor-plugin/plugin.json` / `.claude-plugin/plugin.json` | Harness manifests; same skills tree underneath |
| `skills/sr-*` | Skill wrappers (`SKILL.md`) agents invoke |
| `skills/sr-search/` | Python engine (`uv` project, warehouse, dashboard, CLI) |
| `hooks/` | Session-start hooks (dashboard + shim rectify — never ingest/migrate) |

Cursor’s “add plugins from folder” UI expects a **marketplace** manifest (`.cursor-plugin/marketplace.json`). Pointing it at this repo fails on purpose — stockroom is a plugin, not a marketplace. The catalog lives in [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins).

## Runtime home

After `sr-initialize`, machine-local state lives under stockroom home — `$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable with `STOCKROOM_HOME`:

| Artifact | What it is |
| --- | --- |
| DuckDB warehouse | Session/message/tool/embedding tables (single file under home) |
| Torch freeze | Hashed requirements (+ index sidecar) so heal can reinstall the same wheel |
| On-path shim | `~/.local/bin/stockroom` — baked engine dir; succeed-or-refuse |
| Nightly schedule | Optional cron / launchd entry for ingest + embed |

Optional ingest overrides: `STOCKROOM_CURSOR_ROOT`, `STOCKROOM_CLAUDE_ROOT`, `STOCKROOM_AI_TRACKING_DB`. More on querying the warehouse without another chat turn: [Advanced CLI](../advanced/cli.md).

## Local plugin load

While iterating on the plugin itself, load a checkout instead of the marketplace — see [Local plugin load](../contributing/development.md#local-plugin-load) in the contributor guide. That path is not supported end-user onboarding.
