---
name: sr-query
description: Run read-only SQL against your local warehouse of agentic-coding history (sessions, messages, tool calls, embeddings). Reach for this on exact or structured lookups — known ids, WHERE filters, counts, GROUP BY, joins, aggregations — not meaning-based search (that is sr-semantic).
enable-model-invocation: true
---

# sr-query

`sr-query` runs **read-only SQL** against the stockroom warehouse — the single-file DuckDB database of your captured Cursor + Claude Code history. The surface is read-only by construction: DuckDB rejects any write attempted through it, so you cannot corrupt anything by querying.

## When to use sr-query

Reach for `sr-query` when the question has a **known shape** and the answer is an exact or structured lookup over fields you can name:

- A specific row by id (`WHERE message_id = '…'`, `WHERE session_id = '…'`).
- Filters, counts, and rollups (`COUNT(*)`, `GROUP BY harness`, `WHERE harness = 'claude'`, token sums, date ranges).
- Per-session token rollups via VIEW `session_token_usage` (prefer this over hand-rolled `SUM` on `messages`).
- Joins across `sessions` / `messages` / `tool_calls`.
- "How many", "which sessions", "list the tool calls", "what models" — anything you can express as SQL over named columns.

**Do not** use `sr-query` for *meaning-based* recall ("find conversations about flaky tests"). SQL `ILIKE` is a literal substring match, not semantic search — for meaning, use the **`sr-semantic`** skill. When you are not sure which is right, that judgement belongs to the **`sr-search`** skill.

## How to invoke the engine

```bash
stockroom query "SELECT DISTINCT harness FROM sessions ORDER BY harness"
```

You can also pipe SQL from stdin with `-`:

```bash
echo "SELECT count(*) FROM messages" | stockroom query -
```

If `command -v stockroom` fails, the machine isn't set up yet: tell the user to run the **`sr-initialize`** skill, and don't attempt any other invocation.

## Output discipline: `--format` and `--detail`

**The defaults are already safe for an agent** — a bare call gives bounded, parseable output — so reach for the flags only when a situation calls for it.

### `--format` — output shape, default `tsv`

| Value | Shape | Use it when |
|-------|-------|-------------|
| `tsv` *(default)* | Header row + tab-separated rows, no count trailer | Default. Stream-friendly for you and for unix pipes (`cut`, `awk`, `wc -l`). |
| `json` | A single `{"columns": [...], "rows": [...]}` object | A **user** asks for structured/machine output, or you want to hand it to `jq`. |
| `table` | Column-aligned ASCII with a `(N rows)` trailer | A **user** asks for something human-readable / a copy-paste command to look at. |

Lead with the default `tsv`. Offer `--format table` or `--format json` **when the user asks** for human-readable or structured output — "these other shapes exist if you want them."

### `--detail` — per-field width, default `snippet`

Wide string fields (notably `messages.text` and `tool_calls.tool_input`) are truncated **at read time** so one fat column can't flood your context. Truncation is display-only — full text is always retrievable.

| Value | Budget per field | Use it when |
|-------|------------------|-------------|
| `compact` | ~40 chars | Scanning many candidate rows cheaply before picking one. |
| `snippet` *(default)* | ~120 chars | Default. Enough to recognize a row without dumping it. |
| `full` | unbounded, single-line | You need the whole field length, and single-line collapse is fine (tables/TSV stay safe). |
| `raw` | unbounded, exact whitespace | You need text **as stored** — newlines and internal spaces intact. Prefer with `--format json`. |

An over-budget field is elided with a marker reporting how many characters were hidden, e.g. `…(+2284)`. That marker is your signal that more exists: if you actually need it, re-fetch **just that field for the specific row** at `--detail full` (length) or `--format json --detail raw` (exact whitespace) — see guardrails.

## Guardrails

These are the failure modes this skill exists to prevent:

- **Don't blow out your context.** Never `SELECT *` (or a wide `text` column) at `--detail full`/`raw` across many rows. Instead: scan narrow at `--detail compact`/`snippet` with an explicit column list and a `LIMIT`, identify the row you want, then re-fetch only that row's wide field with a `WHERE` on its id. A single `SELECT text FROM messages WHERE message_id = '…'` is cheap; `SELECT * FROM messages --detail full` is a context bomb. When you need **exact** whitespace (markdown tables, code blocks), use `--format json --detail raw`.
- **It is read-only — never attempt writes.** `INSERT` / `UPDATE` / `DELETE` / `CREATE` all fail (`query failed: …`). Do not retry a write through a different phrasing; the surface only interrogates.
- **`tool_input` is heterogeneous JSON.** Its keys vary per tool (`Shell` has `command`, `Read` has `path`, …), so a naive `tool_input->>'key'` can raise a cast error. Extract safely by filtering `tool_name` in a subquery/CTE first and using the explicit function:

```bash
stockroom query "SELECT json_extract_string(tool_input, '\$.command') AS cmd
  FROM (SELECT tool_input FROM tool_calls WHERE tool_name = 'Shell') LIMIT 5"
```

### Handle errors without thrashing

Each failure is a clean stderr message + exit code — read it and take the matching action, don't loop:

| Message | Exit | What it means / next action |
|---------|------|------------------------------|
| `error: empty query (…)` | 2 | No SQL was passed. Provide a statement. |
| `error: no warehouse found at … — run \`stockroom ingest\` first` | 1 | The warehouse hasn't been built. Tell the user to run `stockroom ingest` (or `sr-initialize` if the machine was never set up); don't retry the query. |
| `query failed: …` | 1 | Invalid SQL, or a write was rejected. Fix the statement (read the DuckDB message) — don't re-run the same SQL. |

## What's in the warehouse

The visual schema is [`references/warehouse-schema.md`](references/warehouse-schema.md).

The picture does not carry these meanings:

- `sessions.project_id` is the verbatim project-dir slug — the grouping key (for Cursor CLI chats, the chats hash directory). `cwd` is a real path and may be `NULL`. `workspace_key` is a separate nullable cross-harness path rollup. `entrypoint` is surface provenance when known and may be `NULL` — `SELECT DISTINCT entrypoint` rather than guessing literals.
- `messages.text` is the whole turn; thinking/reasoning is **not** captured.
- `tool_calls` stores tool **inputs only**, never outputs.

Always join on the uniform `message_id` / `(harness, session_id)`, never on the `source_*` provenance columns. A value that only exists at one grain per harness is honestly `NULL` for the other (e.g. `messages.model` is Claude-only; `sessions.models` is Cursor-only; the same dual-grain honesty applies to tokens).

Prefer VIEW `session_token_usage` for conversation rollups. Columns: `*_from_messages` (SUM of message tokens), `*_native` (session columns), `*_total` (`COALESCE(native, from_messages)`), `token_grain` (`'session'`|`'message'`|`'none'`). Totals are warehouse rollups of reported fields, not vendor invoices. Do not also `SUM` message tokens on top of `*_total`.

`_sync_state` is ingest watermark bookkeeping; not interesting to query.

## Worked examples

All verified against a real warehouse.

```bash
# Which harnesses are present? (tsv default)
stockroom query "SELECT DISTINCT harness FROM sessions ORDER BY harness"

# Session counts per harness, human-readable for a user:
stockroom query --format table "SELECT harness, count(*) AS n FROM sessions GROUP BY harness ORDER BY n DESC"

# Busiest tools:
stockroom query "SELECT tool_name, count(*) AS calls FROM tool_calls GROUP BY tool_name ORDER BY calls DESC LIMIT 5"

# Scan candidate messages cheaply, then re-fetch the one you want in full:
stockroom query --detail compact "SELECT message_id, text FROM messages WHERE text ILIKE '%flaky test%' LIMIT 10"
stockroom query --format json --detail raw \
  "SELECT text FROM messages WHERE message_id = '<id-from-the-scan>'"

# Structured output for a user/tool to consume:
stockroom query --format json "SELECT harness, session_id, title FROM sessions WHERE title IS NOT NULL LIMIT 5"

# Per-session token rollups (VIEW session_token_usage):
stockroom query --format table \
  "SELECT harness, session_id, input_tokens_total, output_tokens_total, token_grain
   FROM session_token_usage
   ORDER BY input_tokens_total DESC NULLS LAST
   LIMIT 10"
```

More variants (unbounded tools with activity window, day/harness token rollups, per-harness skill-use SQL): see the [Cookbook](references/cookbook/index.md).

## Cookbook

Gnarly starter SQL: [`references/cookbook/`](references/cookbook/index.md). Open the index, then only the recipe you need.

## Relaying to a human

You are the tool's operator, not its display. Run the SQL, read the result, and **answer the user in natural language**. Don't paste raw tsv at a human unless they asked to see it. When they *do* want the raw output — or a command to run themselves — hand them a `--format table` (to read) or `--format json` (to process) variant.

## Understanding the system

To understand *why* these contracts look the way they do — the packaging, the torch contract, read-only-by-construction, the truncation doctrine, identity/provenance — read the shared system model: [`../sr-search/references/system-model.md`](../sr-search/references/system-model.md).
