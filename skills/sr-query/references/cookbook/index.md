# sr-query cookbook

Verified starter SQL for gnarly warehouse questions. Prefer these over reverse-engineering the dashboard API.

## Recipes

| Recipe | When |
| --- | --- |
| [token-usage.md](token-usage.md) | Per-session / by-harness / by-day token rollups via VIEW `session_token_usage` |
| [tools.md](tools.md) | Full tool-call rankings (beyond dashboard top-10), with activity window + harness |
| [skills-claude.md](skills-claude.md) | Claude skill-use table from warehouse SQL (escape hatch; extractors remain product truth) |
| [skills-cursor.md](skills-cursor.md) | Cursor skill-use table from warehouse SQL (escape hatch; extractors remain product truth) |

## How to run

```bash
stockroom query --format table "<SQL from a recipe>"
```

If `stockroom` is missing, run **`sr-initialize`** first.

## Promotion note

Dashboard metrics / Python extractors (`stockroom.dashboard.skill_usage`) remain the product definition for skill charts. Skill recipes here are ad-hoc full-table escape hatches — keep their caveats and drift triggers in view.
