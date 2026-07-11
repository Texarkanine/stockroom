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

- Prefer **`/sr-search`** (Cursor) or **`/stockroom:sr-search`** (Claude Code) when you are unsure whether the question is structured or meaning-based.
- Use **`/sr-query`** / **`/stockroom:sr-query`** for exact SQL, filters, and counts.
- Use **`/sr-semantic`** / **`/stockroom:sr-semantic`** for recall by meaning.
- Use **`/sr-dashboard`** / **`/stockroom:sr-dashboard`** for the at-a-glance UI (also launched automatically: Cursor on `sessionStart`, Claude Code on `SessionStart`).

## Dashboard notes

The dashboard is a **machine-scoped** singleton on port 58008: it stays up across harness sessions and is not stopped when one IDE closes. After a plugin update moves the engine path, the next session/workspace start replaces a stale owned listener with one from the healed engine. A dashboard started before that identity tracking existed may need one manual stop (`kill` the old `stockroom.dashboard` process) before automatic replace can take over.

If the Cursor auto-dashboard never starts, confirm the third-party plugins setting on the [Install](install.md) page is on, then use `/sr-dashboard` or `stockroom dashboard`.

## Escape hatch

To run query/semantic (and other subcommands) without another agent turn, see [Advanced usage](advanced/index.md).
