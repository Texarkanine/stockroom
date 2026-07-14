# Search

Ask the agent about past work, or slash-invoke a search skill. Prefer **`sr-search`** when you are not sure whether the answer is a structured SQL lookup or meaning-based recall — it routes to the right surface(s) and synthesizes one answer.

After [Quickstart](quickstart.md), the warehouse must already have data ([Load the Warehouse](ingest.md)). Empty results are often a freshness or torch problem, not a bad question — see [Troubleshooting](troubleshooting/index.md).

## How to ask

Natural language is enough (“when did we last fight the dashboard port?”). When you want a specific surface:

| Skill | Cursor | Claude Code |
| --- | --- | --- |
| `sr-search` | `/sr-search` | `/stockroom:sr-search` |
| `sr-query` | `/sr-query` | `/stockroom:sr-query` |
| `sr-semantic` | `/sr-semantic` | `/stockroom:sr-semantic` |

Example:

```text
/sr-search "What was the most-recent time I had to correct an agent's behavior?"
```

Operational flags and recovery tables live in each skill’s `SKILL.md` — this page does not duplicate them. To run the engine without another agent turn, see [Advanced → CLI](../advanced/cli.md) (`stockroom query` / `stockroom semantic`).

## The three search skills

### `sr-search`

The friendly default. It classifies the ask, delegates to `sr-query` and/or `sr-semantic`, and presents one answer with supporting session/message ids.

| The ask | What it does |
| --- | --- |
| Exact or structured (ids, filters, counts, joins) | Routes to `sr-query` |
| Meaning-based (describe the topic, not the id) | Routes to `sr-semantic` |
| Broad or ambiguous (both a nameable shape and a concept) | Runs both, then synthesizes |

If one surface comes back empty or thin, it should try the other before concluding the content is absent. Scores from semantic search are never blended with SQL rows — different kinds of evidence.

### `sr-query`

Read-only SQL against the warehouse (`sessions`, `messages`, `tool_calls`, `embeddings`). Reach for it when the question has a **known shape**: a message or session id, `WHERE` filters, counts, `GROUP BY`, joins, date ranges, token sums.

```bash
stockroom query "SELECT DISTINCT harness FROM sessions ORDER BY harness"
```

The surface is read-only by construction — you cannot corrupt the warehouse by querying. Do **not** use SQL `ILIKE` as a substitute for meaning-based recall; that is `sr-semantic`.

### `sr-semantic`

Vector (meaning-based) search. Reach for it when you can describe the content but not name an id — “conversations about flaky tests,” “where did we debug the warehouse deadlock.”

```bash
stockroom semantic "how does the warehouse locking work"
```

Phrase the query as a short description of the content you want. Embedding/search needs a working torch install ([Torch](troubleshooting/torch.md)); ingest and `sr-query` do not. Weak results on *recent* work often mean ingest caught up but embed has not — [Load the Warehouse](ingest.md).

## What to try next

- Prefer **`sr-search`** unless you already know you want pure SQL or pure vectors.
- Browse metrics and past conversations in the UI: [Dashboard](dashboard.md).
- Skill index for all `sr-*` surfaces: [Skill index](skills.md).
- Stuck on empty/thin results or read-only SQL errors? [Troubleshooting · Search](troubleshooting/index.md#search) · [Torch](troubleshooting/torch.md).
