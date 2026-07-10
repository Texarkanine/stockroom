---
name: sr-semantic
description: Meaning-based (vector) search over your local warehouse of agentic-coding history. Reach for this when the question is about content or concepts you can describe but not name exactly — "conversations about flaky tests", "where did we debug the deadlock" — not exact ids, filters, or counts (that is sr-query).
enable-model-invocation: true
---

# sr-semantic

`sr-semantic` runs **pure vector search** against the stockroom warehouse — the single-file DuckDB database of your captured agentic coding harness history. It embeds your natural-language query and returns a ranked list of the most semantically similar messages. The surface is read-only by construction: you cannot corrupt anything by searching.

## When to use sr-semantic

Reach for `sr-semantic` when the question is about **meaning** — content you can describe but not name exactly:

- "Find conversations about flaky test debugging."
- "Where did we work through the warehouse locking design?"
- Paraphrased or conceptual recall — the stored text won't contain your words verbatim, but it's *about* what you're asking.

**Do not** use `sr-semantic` for exact or structured lookups — a known `session_id`/`message_id`, filters, counts, `GROUP BY`, joins, date ranges. Those have a known shape and belong to the **`sr-query`** skill (raw read-only SQL). When you are not sure which is right, that judgement belongs to the **`sr-search`** skill.

**Phrase the query as a description of the content you want**, in natural language: a short phrase or sentence naming the topic, activity, or concept ("incremental re-embed of new content", "fixing the REUSE licensing layout"). Do not add any instruction preamble — the model's query prefix is applied automatically; hand-adding it would double it.

## How to invoke the engine

```bash
stockroom semantic "how does the warehouse locking work"
```

If `command -v stockroom` fails, the machine isn't set up yet: tell the user to run the **`sr-initialize`** skill, and don't attempt any other invocation.

One runtime note: the model loader may print a Hugging Face hub notice / weight-loading progress to **stderr** — stdout stays clean for pipes; ignore the noise.

## Output discipline: `-k`, `--format`, and `--detail`

**The defaults are already safe for an agent**, so reach for the flags only when a situation calls for it.

### `-k` / `--limit` — result count, default 10

Lower it (`-k 3`) when you expect one obvious winner; raise it when you're casting wide before narrowing. Must be a positive integer.

### `--format` — output shape, default `tsv`

| Value | Shape | Use it when |
|-------|-------|-------------|
| `tsv` *(default)* | Header `rank score harness role preview` + tab-separated rows, no count trailer | Default. Stream-friendly for you and for unix pipes. |
| `json` | A single `{"results": [...]}` object — each result **additionally carries `session_id` and `message_id`** and a numeric `score` | You need the hit's **ids** (e.g. for the full-text handoff below), a **user** asks for structured output, or you want `jq`. |
| `table` | Column-aligned ASCII with a `(N results)` trailer | A **user** asks for something human-readable / a copy-paste command to look at. |

Lead with the default `tsv`. Offer `--format table` or `--format json` **when the user asks** for human-readable or structured output.

`score` is cosine **similarity** (higher = closer, ~0–1). Scores are *relative* quality within this corpus and query — read the previews to judge relevance; don't threshold on an absolute score.

### `--detail` — preview width, default `snippet`

The `preview`/`text` field is truncated **at read time** so ranked previews can't flood your context. Truncation is display-only — full text is always retrievable.

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
stockroom query --detail full \
  "SELECT text FROM messages WHERE message_id = '<message_id-from-the-json>'"
```

- **It is read-only — never attempt writes.** The surface only searches.
- **Weak results for recent work usually mean stale embeddings, not absence.** Semantic search only sees what has been *embedded*, and embeddings can lag ingestion. Before re-phrasing the same query in a loop, check coverage — and if it lags, suggest the user run the (incremental) embed pass:

```bash
stockroom query "SELECT
  (SELECT count(DISTINCT owner_id) FROM embeddings WHERE owner_table = 'messages') AS embedded_messages,
  (SELECT count(*) FROM messages) AS total_messages"
# lagging badly? -> stockroom embed   (incremental; needs torch)
```

- **Re-phrase, don't repeat.** If results miss, one reworded query (different vocabulary for the same concept) is reasonable; more than that means the content likely isn't there or isn't embedded — switch strategy (`sr-query` keyword `ILIKE`, or the coverage check above) instead of thrashing.

### Handle errors without thrashing

Each failure is a clean stderr message + exit code — read it and take the matching action, don't loop:

| Message | Exit | What it means / next action |
|---------|------|------------------------------|
| `error: empty query (…)` | 2 | No search text was passed. Provide a query. |
| `error: --limit must be a positive integer` | 2 | Bad `-k`. Fix the number. |
| `error: no warehouse found at … — run \`stockroom ingest\` first` | 1 | The warehouse hasn't been built. Tell the user to run `stockroom ingest` (or `sr-initialize` if the machine was never set up); don't retry. |
| `ModuleNotFoundError: No module named 'torch'` | — | Environment problem, not a query problem (this surface needs torch at query time). Don't retry; tell the user to re-run `sr-initialize` to re-provision torch. |

## Worked examples

All verified against a real warehouse.

```bash
# Default: top 10, bounded previews (tsv)
stockroom semantic "how does the warehouse locking work"

# Expecting one obvious winner — keep it tight:
stockroom semantic -k 3 "incremental re-embed of new content"

# Need the ids (for the full-text handoff), or structured output:
stockroom semantic --format json -k 2 "flock sidecar lock"

# Human-readable, terse previews, for a user to eyeball:
stockroom semantic --format table --detail compact -k 3 "REUSE licensing layout"
```

And the full-text handoff pair (scan semantically, then fetch one whole message with `sr-query`):

```bash
stockroom semantic --format json -k 5 "flock sidecar lock"
# ...pick the winning message_id from the json, then:
stockroom query --detail full \
  "SELECT text FROM messages WHERE message_id = 'fcf35cbe-…#51'"
```

## Relaying to a human

You are the tool's operator, not its display. Run the search, read the previews, and **answer the user in natural language** — cite the relevant hit(s), fetch full text only when the answer needs it. Don't paste raw tsv at a human unless they asked to see it. When they *do* want the raw output — or a command to run themselves — hand them a `--format table` (to read) or `--format json` (to process) variant.

## Understanding the system

To understand *why* these contracts look the way they do — the torch contract, the embedding pipeline and its staleness model, read-only-by-construction, the truncation doctrine — read the shared system model: [`../sr-search/references/system-model.md`](../sr-search/references/system-model.md).
