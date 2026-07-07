---
name: sr-query
description: Run read-only SQL against your local warehouse of agentic-coding history (sessions, messages, tool calls, embeddings). Reach for this on exact or structured lookups — known ids, WHERE filters, counts, GROUP BY, joins, aggregations — not meaning-based search (that is sr-semantic).
enable-model-invocation: true
---

# sr-query

`sr-query` runs **read-only SQL** against the stockroom warehouse — the single-file DuckDB database of your captured Cursor + Claude Code history. It is the raw, full-power query surface; this skill is the safe, ergonomic way for an agent to drive it without flooding its own context window or burning failed tool calls.

The warehouse is **read-only through this surface by construction**: it is rebuildable ETL output, and DuckDB rejects any write attempted through it. You cannot corrupt anything by querying.

## When to use sr-query

Reach for `sr-query` when the question has a **known shape** and the answer is an exact or structured lookup over fields you can name:

- A specific row by id (`WHERE message_id = '…'`, `WHERE session_id = '…'`).
- Filters, counts, and rollups (`COUNT(*)`, `GROUP BY harness`, `WHERE harness = 'claude'`, token sums, date ranges).
- Joins across `sessions` / `messages` / `tool_calls`.
- "How many", "which sessions", "list the tool calls", "what models" — anything you can express as SQL over named columns.

**Do not** use `sr-query` for *meaning-based* recall ("find conversations about flaky tests"). SQL `ILIKE` is a literal substring match, not semantic search — for meaning, use the **`sr-semantic`** skill. When you are not sure which is right, that judgement belongs to the **`sr-search`** skill.

## How to invoke the engine

The engine lives inside the `sr-search` skill (it is the shared stockroom engine; `sr-query` has no Python of its own). Resolve its directory **once per session** via the plugin-root env var, with a filesystem fallback for symlinked dev installs, then invoke through the torch-safe run contract:

```bash
# Resolve the engine dir once; reuse $APP_DIR for the rest of the session.
APP_DIR="${CURSOR_PLUGIN_ROOT:+$CURSOR_PLUGIN_ROOT/skills/sr-search}"
if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR" ]; then
  APP_DIR="$(dirname "$(find -L ~/.cursor/plugins -path '*/stockroom/*/skills/sr-search/pyproject.toml' 2>/dev/null | head -1)")"
fi

PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.query "SELECT DISTINCT harness FROM sessions ORDER BY harness"
```

Three details are load-bearing — omit any one and the call fails or misbehaves:

- **`PYTHONPATH="$APP_DIR/src"`** — the engine is a run-in-place project (`[tool.uv] package = false`), so `stockroom` is not installed on `sys.path`; without this you get `ModuleNotFoundError: No module named 'stockroom'`.
- **`--no-sync`** — never let `uv` sync this project. A bare sync strips the out-of-band torch install (the project's torch contract). `sr-query` itself does not need torch, but its sibling surfaces share the environment.
- **`--no-config`** — keep ambient `~/.config/uv/uv.toml` out of resolution (hermetic, matches the repo's `Makefile`).

You can also pipe SQL from stdin with `-`:

```bash
echo "SELECT count(*) FROM messages" | PYTHONPATH="$APP_DIR/src" \
  uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom.query -
```

## Output discipline: `--format` and `--detail`

Two independent axes control output. **The defaults are already safe for an agent** — a bare call gives bounded, parseable output — so reach for the flags only when a situation calls for it.

### `--format` — output shape, default `tsv`

| Value | Shape | Use it when |
|-------|-------|-------------|
| `tsv` *(default)* | Header row + tab-separated rows, no count trailer | Default. Stream-friendly for you and for unix pipes (`cut`, `awk`, `wc -l`). |
| `json` | A single `{"columns": [...], "rows": [...]}` object | A **user** asks for structured/machine output, or you want to hand it to `jq`. |
| `table` | Column-aligned ASCII with a `(N rows)` trailer | A **user** asks for something human-readable / a copy-paste command to look at. |

Lead with the default `tsv`. Offer `--format table` or `--format json` **when the user asks** for human-readable or structured output — "these other shapes exist if you want them."

### `--detail` — per-field width, default `snippet`

Wide string fields (notably `messages.text` and `tool_calls.tool_input`) are truncated **at read time** so one fat column can't flood your context. Full content always stays whole in the warehouse — this is a display bound only.

| Value | Budget per field | Use it when |
|-------|------------------|-------------|
| `compact` | ~40 chars | Scanning many candidate rows cheaply before picking one. |
| `snippet` *(default)* | ~120 chars | Default. Enough to recognize a row without dumping it. |
| `full` | unbounded | You need the **whole** field — typically a re-fetch of one row after a snippet showed `…(+N)`. |

An over-budget field is elided with a marker reporting how many characters were hidden, e.g. `…(+2284)`. That marker is your signal that more exists: if you actually need it, re-fetch **just that field for the specific row** at `--detail full` (see guardrails).

## Guardrails

These are the failure modes this skill exists to prevent:

- **Don't blow out your context.** Never `SELECT *` (or a wide `text` column) at `--detail full` across many rows. Instead: scan narrow at `--detail compact`/`snippet` with an explicit column list and a `LIMIT`, identify the row you want, then re-fetch only that row's wide field at `--detail full` with a `WHERE` on its id. A single `SELECT text FROM messages WHERE message_id = '…'` at `--detail full` is cheap; `SELECT * FROM messages --detail full` is a context bomb.
- **It is read-only — never attempt writes.** `INSERT` / `UPDATE` / `DELETE` / `CREATE` all fail (`query failed: …`). Do not retry a write through a different phrasing; the surface only interrogates.
- **`tool_input` is heterogeneous JSON.** Its keys vary per tool (`Shell` has `command`, `Read` has `path`, …). A naive `tool_input->>'key'` can raise a cast error when the planner evaluates it on a differently-shaped row. Extract safely by filtering `tool_name` in a subquery/CTE first and using the explicit function:

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.query "SELECT json_extract_string(tool_input, '\$.command') AS cmd
    FROM (SELECT tool_input FROM tool_calls WHERE tool_name = 'Shell') LIMIT 5"
```

### Handle errors without thrashing

Each failure is a clean stderr message + exit code — read it and take the matching action, don't loop:

| Message | Exit | What it means / next action |
|---------|------|------------------------------|
| `error: empty query (…)` | 2 | No SQL was passed. Provide a statement. |
| `error: no warehouse found at … — run \`python -m stockroom.ingest\` first` | 1 | The warehouse hasn't been built. Tell the user to run ingest; don't retry the query. |
| `query failed: …` | 1 | Invalid SQL, or a write was rejected. Fix the statement (read the DuckDB message) — don't re-run the same SQL. |

## What's in the warehouse

**Discover the live schema first** — this stays correct as the schema evolves:

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.query "SELECT table_name, column_name, data_type
    FROM information_schema.columns ORDER BY table_name, ordinal_position"
```

Quick reference of the load-bearing columns **as of migrations 0001–0003** (confirm with the introspection query above):

- **`sessions`** — one row per conversation. `harness` (`'cursor'`|`'claude'`), `session_id`, `project_id` (verbatim project-dir slug — the grouping key), `cwd` (real path, may be `NULL`), `models` (`VARCHAR[]`, Cursor only), `title`, `git_branch`, `is_subagent`, `parent_session_id`, `started_at`, `ended_at`. PK `(harness, session_id)`.
- **`messages`** — one row per turn. `message_id = '{session_id}#{ordinal}'` (uniform across harnesses), `parent_id`, `ordinal`, `role` (`'user'`|`'assistant'`), `text` (whole; thinking is **not** captured), `model` (per-message, Claude only), `ts`, and four token `BIGINT`s: `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens`. PK `(harness, session_id, message_id)`.
- **`tool_calls`** — tool **inputs only** (never outputs). `message_id` (the turn that emitted it), `ordinal`, `tool_name`, `tool_input` (heterogeneous `JSON`, stored whole — see the guardrail). PK `(harness, session_id, message_id, ordinal)`.
- **`embeddings`** — per-chunk vectors for semantic search (`owner_table`, `owner_id`, `chunk_index`, `embed_model`, `vector FLOAT[384]`). You rarely query this directly — use the `sr-semantic` skill.
- **`_sync_state`** — ingest watermark bookkeeping; not interesting to query.

Identity notes worth knowing before you write a join: native ids (e.g. Claude's `uuid`) are demoted to `source_*` provenance columns and are **never** join keys — join on the uniform `message_id` / `(harness, session_id)`. A value that only exists at one grain per harness is honestly `NULL` for the other (e.g. `messages.model` is Claude-only; `sessions.models` is Cursor-only).

## Worked examples

All verified against a real warehouse. Each assumes `$APP_DIR` is resolved as above; prefix every command with `PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom.query`.

```bash
# Which harnesses are present? (tsv default)
"SELECT DISTINCT harness FROM sessions ORDER BY harness"

# Session counts per harness, human-readable for a user:
--format table "SELECT harness, count(*) AS n FROM sessions GROUP BY harness ORDER BY n DESC"

# Busiest tools:
"SELECT tool_name, count(*) AS calls FROM tool_calls GROUP BY tool_name ORDER BY calls DESC LIMIT 5"

# Scan candidate messages cheaply, then re-fetch the one you want in full:
--detail compact "SELECT message_id, text FROM messages WHERE text ILIKE '%flaky test%' LIMIT 10"
--detail full    "SELECT text FROM messages WHERE message_id = '<id-from-the-scan>'"

# Structured output for a user/tool to consume:
--format json "SELECT harness, session_id, title FROM sessions WHERE title IS NOT NULL LIMIT 5"
```

## Relaying to a human

You are the tool's operator, not its display. Run the SQL, read the result, and **answer the user in natural language**. Don't paste raw tsv at a human unless they asked to see it. When they *do* want the raw output — or a command to run themselves — hand them a `--format table` (to read) or `--format json` (to process) variant.
