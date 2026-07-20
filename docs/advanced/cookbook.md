# Query cookbook

Copy-paste starter SQL for gnarly warehouse questions — the same recipes agents load from the `sr-query` skill.

**SSOT:** edit recipe bodies under [`skills/sr-query/references/cookbook/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-query/references/cookbook) (this page only wraps them). Material "Edit this page" hits the wrapper, not the SQL.

## When to use Advanced cookbook

- You want the full tools table, richer token rollups, or per-harness skill-use SQL without reverse-engineering the dashboard.
- You already have `stockroom` on `PATH` and a warehouse (see [CLI](cli.md)).

## Promotion and drift

| Kind | Product truth | Cookbook role |
| --- | --- | --- |
| Token rollups | VIEW `session_token_usage` | Longer variants that still `SELECT` from the VIEW |
| Tool rankings | Pure SQL (dashboard top-10 is a UI cap) | Unbounded / windowed `GROUP BY` starters |
| Skill use | Python extractors in `stockroom.dashboard.skill_usage` | Ad-hoc SQL escape hatches with caveats — **not** a second product definition |

When extractors or the VIEW change, update the skill recipe (and its drift trigger note). Do not clone SQL into the User Guide.

## Recipes

--8<-- "skills/sr-query/references/cookbook/token-usage.md"

--8<-- "skills/sr-query/references/cookbook/tools.md"

--8<-- "skills/sr-query/references/cookbook/skills-claude.md"

--8<-- "skills/sr-query/references/cookbook/skills-cursor.md"
