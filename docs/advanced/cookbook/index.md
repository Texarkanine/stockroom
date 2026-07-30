# Query cookbook

Copy-paste starter SQL for the questions that are awkward to reinvent every time — token rollups, full tool rankings, and per-harness skill use — run through the same `stockroom query` surface your agents use.

## Prerequisites

- `stockroom` on `PATH` (after `sr-initialize`)
- A warehouse you can already query — see [CLI](../cli.md) if you need a refresher

```bash
stockroom query --format table "SELECT count(*) FROM sessions"
```

## Recipes

Each recipe page is the same markdown file the `sr-query` skill ships. Edit the SQL under [`skills/sr-query/references/cookbook/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-query/references/cookbook) in the repo; Material "Edit this page" on a recipe hits the docs symlink path.

| Recipe | Use it when you want… |
| --- | --- |
| [Token usage](token-usage.md) | Per-session / by-harness / by-day totals from VIEW `session_token_usage` |
| [Tools](tools.md) | Full `tool_name` ranking (activity window), or one conversation |
| [Skills — Claude](skills-claude.md) | Claude skill × invoker counts (warehouse window or one session) |
| [Skills — Cursor](skills-cursor.md) | Cursor skill × invoker counts (warehouse window or one session) |

## How to run a recipe

Copy a statement from a recipe page, then:

```bash
stockroom query --format table "<paste SQL here>"
```

Prefer `--format table` when you are reading the result yourself; use the default `tsv` (or `--format json`) when piping into other tools.
