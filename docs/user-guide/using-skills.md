# Using skills

Most day-to-day use goes through the `sr-*` skills. Ask the agent in natural language, or slash-invoke a skill when you want a specific surface.

Invocation forms differ by harness. Engine calls after setup are always `stockroom <subcommand>` on PATH; only the skill slash forms below are harness-specific.

## Skills table

| Skill | Cursor | Claude Code | Role |
| --- | --- | --- | --- |
| `sr-initialize` | `/sr-initialize` | `/stockroom:sr-initialize` | Machine setup (torch, shim, schedule, first ingest) |
| `sr-search` | `/sr-search` | `/stockroom:sr-search` | Friendly default search (routes to query / semantic) |
| `sr-query` | `/sr-query` | `/stockroom:sr-query` | Read-only SQL against the warehouse |
| `sr-semantic` | `/sr-semantic` | `/stockroom:sr-semantic` | Meaning-based (vector) search |
| `sr-dashboard` | `/sr-dashboard` | `/stockroom:sr-dashboard` | Open the local metrics dashboard |

Operational flags, recovery tables, and procedures live in each skill’s `SKILL.md` — this page does not duplicate them.

## After setup

- Prefer **`sr-search`** when you are unsure whether the question is structured or meaning-based — details: [Search](search.md).
- Use **`sr-query`** / **`sr-semantic`** when you already know you want pure SQL or pure vectors ([Search](search.md)).
- Open the metrics UI with **`sr-dashboard`** (also auto-launched on session start when hooks are registered) — details: [Dashboard](dashboard.md).

## Escape hatch

To run query/semantic (and other subcommands) without another agent turn, see [Advanced usage](../advanced/index.md).
