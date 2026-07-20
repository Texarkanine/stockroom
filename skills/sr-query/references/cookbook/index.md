# sr-query cookbook

Starter SQL for gnarly warehouse questions. Open a recipe only after you know you need that shape.

| Recipe | When |
| --- | --- |
| [token-usage.md](token-usage.md) | Token rollups via VIEW `session_token_usage` |
| [tools.md](tools.md) | Full tool rankings (activity window + harness) |
| [skills-claude.md](skills-claude.md) | Claude skill × invoker SQL |
| [skills-cursor.md](skills-cursor.md) | Cursor skill × invoker SQL |

```bash
stockroom query --format table "<SQL from a recipe>"
```

Skill charts’ product definition is still `stockroom.dashboard.skill_usage` — these skill recipes are ad-hoc escape hatches.
