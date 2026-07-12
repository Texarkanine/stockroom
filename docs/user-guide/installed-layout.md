# Installed layout

Stockroom installs as a Plugin into your chosen harness, but it has some surprises:

1. it carries a whole python app inside the `sr-search` skill
2. The setup (`sr-initialize` skill) will put some things on your machine:
	- a `stockroom` CLI on your PATH
	- a `warehouse.duckdb` file in `$XDG_DATA_HOME/stockroom` (`~/.local/share/stockroom` by default)
	- (optional) a `crontab` or `launchd` schedule entry for nightly ingest + embed

## Plugin payload

This all lands in wherever your chosen harness stores plugin data:

| Path | Role |
| --- | --- |
| `.cursor-plugin/plugin.json` / `.claude-plugin/plugin.json` | Harness manifests; same skills tree underneath |
| `skills/sr-*` | Skill wrappers (`SKILL.md`) agents invoke |
| `skills/sr-search/` | Python engine (`uv` project, warehouse, dashboard, CLI) |
| `hooks/` | Session-start hooks (dashboard + shim rectify — never ingest/migrate) |

## Runtime home

After `sr-initialize`, machine-local state lives under stockroom home — `$XDG_DATA_HOME/stockroom` or `~/.local/share/stockroom`, overridable with `STOCKROOM_HOME`:

| Path | What it is |
| --- | --- |
| `$STOCKROOM_HOME/warehouse.duckdb` | **DuckDB warehouse:** session/message/tool/embedding tables |
| `$STOCKROOM_HOME/torch-requirements.txt` | **Torch freeze:** hashed requirements so heal can reinstall the same wheel |
| `$STOCKROOM_HOME/torch-index` | **Torch index sidecar:** https wheel index URL used when the freeze was written |
| `~/.local/bin/stockroom` | **On-path shim:** bakes the correct `uv` invocation to run Stockroom + Torch offline, from the plugin payload directory |
