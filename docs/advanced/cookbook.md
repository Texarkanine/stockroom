# Query cookbook

The same starter SQL agents load from `sr-query` — copy from here or from the skill tree.

**SSOT:** edit recipe bodies under [`skills/sr-query/references/cookbook/`](https://github.com/Texarkanine/stockroom/tree/main/skills/sr-query/references/cookbook). Material "Edit this page" hits this wrapper, not the SQL.

Skill-use recipes approximate extractors in SQL; dashboard metrics / `stockroom.dashboard.skill_usage` remain chart truth. When extractors or VIEW `session_token_usage` change, update the skill recipe.

## Recipes

--8<-- "skills/sr-query/references/cookbook/token-usage.md"

--8<-- "skills/sr-query/references/cookbook/tools.md"

--8<-- "skills/sr-query/references/cookbook/skills-claude.md"

--8<-- "skills/sr-query/references/cookbook/skills-cursor.md"
