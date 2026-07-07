---
name: sr-semantic
description: Meaning-based (vector) search over your local warehouse of agentic-coding history. Reach for this when the question is about content or concepts you can describe but not name exactly — "conversations about flaky tests", "where did we debug the deadlock" — not exact ids, filters, or counts (that is sr-query).
enable-model-invocation: true
---

# sr-semantic

`sr-semantic` runs **pure vector search** against the stockroom warehouse — the single-file DuckDB database of your captured agentic coding harness history. It embeds your natural-language query with the same local model that embedded the stored messages, runs cosine KNN over the HNSW index, and returns a ranked list of the most semantically similar messages. This skill is the safe, ergonomic way for an agent to drive that surface without flooding its own context window or burning failed tool calls.

The warehouse is **read-only through this surface by construction**: DuckDB rejects any write attempted through it. You cannot corrupt anything by searching.

## When to use sr-semantic

Reach for `sr-semantic` when the question is about **meaning** — content you can describe but not name exactly:

- "Find conversations about flaky test debugging."
- "Where did we work through the warehouse locking design?"
- Paraphrased or conceptual recall — the stored text won't contain your words verbatim, but it's *about* what you're asking.

**Do not** use `sr-semantic` for exact or structured lookups — a known `session_id`/`message_id`, filters, counts, `GROUP BY`, joins, date ranges. Those have a known shape and belong to the **`sr-query`** skill (raw read-only SQL). When you are not sure which is right, that judgement belongs to the **`sr-search`** skill.

**Phrase the query as a description of the content you want**, in natural language: a short phrase or sentence naming the topic, activity, or concept ("incremental re-embed of new content", "fixing the REUSE licensing layout"). Do not add any instruction preamble — the model's asymmetric query prefix is applied automatically; hand-adding it would double it.

## How to invoke the engine

The engine lives inside the `sr-search` skill (it is the shared stockroom engine; `sr-semantic` has no Python of its own). Resolve its directory **once per session** via the plugin-root env var, with a filesystem fallback for symlinked dev installs, then invoke through the torch-safe run contract:

```bash
# Resolve the engine dir once; reuse $APP_DIR for the rest of the session.
APP_DIR="${CURSOR_PLUGIN_ROOT:+$CURSOR_PLUGIN_ROOT/skills/sr-search}"
if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR" ]; then
  APP_DIR="$(dirname "$(find -L ~/.cursor/plugins -path '*/stockroom/*/skills/sr-search/pyproject.toml' 2>/dev/null | head -1)")"
fi

PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.semantic "how does the warehouse locking work"
```

Three details are load-bearing — omit any one and the call fails or misbehaves:

- **`PYTHONPATH="$APP_DIR/src"`** — the engine is a run-in-place project (`[tool.uv] package = false`), so `stockroom` is not installed on `sys.path`; without this you get `ModuleNotFoundError: No module named 'stockroom'`.
- **`--no-sync`** — never let `uv` sync this project. A bare sync strips the out-of-band torch install — and **this surface needs torch at query time** (the encoder embeds your query), so for `sr-semantic` this flag is doubly load-bearing.
- **`--no-config`** — keep ambient `~/.config/uv/uv.toml` out of resolution (hermetic).

Two runtime notes: if torch is **missing** (`ModuleNotFoundError: No module named 'torch'`), that is an environment problem, not a query problem — do not retry; tell the user torch needs re-provisioning (in the stockroom repo, `make torch`). And the model loader may print a Hugging Face hub notice / weight-loading progress to **stderr** — stdout stays clean for pipes; ignore the noise.

## Output discipline: `-k`, `--format`, and `--detail`

Three independent axes control output. **The defaults are already safe for an agent** — a bare call gives ≤10 ranked rows with bounded previews — so reach for the flags only when a situation calls for it.

### `-k` / `--limit` — result count, default 10

Lower it (`-k 3`) when you expect one obvious winner; raise it when you're casting wide before narrowing. Must be a positive integer.

### `--format` — output shape, default `tsv`

Shapes and columns as rendered by the shared `stockroom.render` layer (verify against a live call if they ever look different):

| Value | Shape | Use it when |
|-------|-------|-------------|
| `tsv` *(default)* | Header `rank score harness role preview` + tab-separated rows, no count trailer | Default. Stream-friendly for you and for unix pipes. |
| `json` | A single `{"results": [...]}` object — each result **additionally carries `session_id` and `message_id`** and a numeric `score` | You need the hit's **ids** (e.g. for the full-text handoff below), a **user** asks for structured output, or you want `jq`. |
| `table` | Column-aligned ASCII with a `(N results)` trailer | A **user** asks for something human-readable / a copy-paste command to look at. |

Lead with the default `tsv`. Offer `--format table` or `--format json` **when the user asks** for human-readable or structured output.

`score` is cosine **similarity** (higher = closer, ~0–1). Scores are *relative* quality within this corpus and query — read the previews to judge relevance; don't threshold on an absolute score.

### `--detail` — preview width, default `snippet`

The `preview`/`text` field is truncated **at read time** so ranked previews can't flood your context. Full message text always stays whole in the warehouse — this is a display bound only.

| Value | Budget | Use it when |
|-------|--------|-------------|
| `compact` | ~40 chars | Scanning many candidates cheaply before picking one. |
| `snippet` *(default)* | ~120 chars | Default. Enough to recognize a hit without dumping it. |
| `full` | unbounded | Almost never here — prefer the `sr-query` handoff below for whole text. |

An over-budget preview is elided with a marker reporting how many characters were hidden, e.g. `…(+2539)`. That marker is your signal that more exists.

## Guardrails

These are the failure modes this skill exists to prevent:

- **Don't blow out your context.** Never combine `--detail full` with a large `-k` — ten untruncated messages can be tens of thousands of characters. Scan at the default `snippet` (or `compact`), pick the hit you want, then fetch **just that one message's whole text** via the **`sr-query` handoff**: re-run with `--format json` to get the hit's `message_id`, then

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.query --detail full \
  "SELECT text FROM messages WHERE message_id = '<message_id-from-the-json>'"
```

- **It is read-only — never attempt writes.** The surface only searches.
- **Weak results for recent work usually mean stale embeddings, not absence.** Semantic search only sees what has been *embedded*, and embeddings can lag ingestion. Before re-phrasing the same query in a loop, check coverage via the `sr-query` handoff — and if it lags, suggest the user run the (incremental) embed pass:

```bash
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.query "SELECT
    (SELECT count(DISTINCT owner_id) FROM embeddings WHERE owner_table = 'messages') AS embedded_messages,
    (SELECT count(*) FROM messages) AS total_messages"
# lagging badly? -> python -m stockroom.embed   (incremental; needs torch)
```

- **Re-phrase, don't repeat.** If results miss, one reworded query (different vocabulary for the same concept) is reasonable; more than that means the content likely isn't there or isn't embedded — switch strategy (`sr-query` keyword `ILIKE`, or the coverage check above) instead of thrashing.

### Handle errors without thrashing

Each failure is a clean stderr message + exit code — read it and take the matching action, don't loop:

| Message | Exit | What it means / next action |
|---------|------|------------------------------|
| `error: empty query (…)` | 2 | No search text was passed. Provide a query. |
| `error: --limit must be a positive integer` | 2 | Bad `-k`. Fix the number. |
| `error: no warehouse found at … — run \`python -m stockroom.ingest\` first` | 1 | The warehouse hasn't been built. Tell the user to run ingest; don't retry. |
| `ModuleNotFoundError: No module named 'torch'` | — | Environment problem (torch stripped/missing). Don't retry; user re-provisions torch. |

## Worked examples

All verified against a real warehouse. Each assumes `$APP_DIR` is resolved as above; prefix every command with `PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom.semantic`.

```bash
# Default: top 10, bounded previews (tsv)
"how does the warehouse locking work"

# Expecting one obvious winner — keep it tight:
-k 3 "incremental re-embed of new content"

# Need the ids (for the full-text handoff), or structured output:
--format json -k 2 "flock sidecar lock"

# Human-readable, terse previews, for a user to eyeball:
--format table --detail compact -k 3 "REUSE licensing layout"
```

And the full-text handoff pair (scan semantically, then fetch one whole message with `sr-query`):

```bash
--format json -k 5 "flock sidecar lock"
# ...pick the winning message_id from the json, then:
PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
  python -m stockroom.query --detail full \
  "SELECT text FROM messages WHERE message_id = 'fcf35cbe-…#51'"
```

## Relaying to a human

You are the tool's operator, not its display. Run the search, read the previews, and **answer the user in natural language** — cite the relevant hit(s), fetch full text only when the answer needs it. Don't paste raw tsv at a human unless they asked to see it. When they *do* want the raw output — or a command to run themselves — hand them a `--format table` (to read) or `--format json` (to process) variant.
