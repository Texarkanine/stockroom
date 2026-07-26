# Skills

Wrapper skills are the agent-facing how-to for Stockroom's engine surfaces. They live under [`skills/`](https://github.com/Texarkanine/stockroom/tree/main/skills) — each skill is a directory with a `SKILL.md` (plus optional `references/`). Skills invoke the engine only as `stockroom <subcommand>`; they do not call `uv` or `make`.

| Skill | Path | Role |
| --- | --- | --- |
| `sr-dashboard` | `skills/sr-dashboard/` | Open / print the local dashboard URL |
| `sr-initialize` | `skills/sr-initialize/` | How to onboard a machine to Stockroom and/or heal an existing installation |
| `sr-query` | `skills/sr-query/` | How to use SQL to query the warehouse |
| `sr-search` | `skills/sr-search/` | How to use the engine to search the warehouse. Also contains the Python `engine` code. |
| `sr-semantic` | `skills/sr-semantic/` | How to search the warehouse w/ Semantic (vector) search |

## Development Loop

1. Edit `skills/<name>/SKILL.md` and any `references/` that skill owns.
2. Reload so the harness picks up the text:
	- **Cursor:** with localdev skills wired, the project mirror under `.cursor/skills/stockroom-local/` follows the checkout (`HARNESS=cursor make local-skills`). Close & re-open Cursor once you make Skill text changes. Do not commit the mirror — localdev installs a pre-commit guard so it stays out of git to help you avoid this.
	- **Claude Code:** load the plugin tree with `claude --plugin-dir /path/to/stockroom` (see [Preparation](../preparation.md)); there is no Cursor-style skills mirror.
3. Exercise the skill in a session.

## Relevant Make Targets

| Target | Role |
| --- | --- |
| `local-skills` | Wire checkout skills (`HARNESS` must be `cursor` or `claude`) |
| `localdev` / `localdev-clean` / `localdev-status` | Full enter / clean / status composition — see [Preparation](../preparation.md) |
