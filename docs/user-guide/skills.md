# Skill index

Stockroom’s agent-facing surfaces are the `sr-*` skills. Ask in natural language, or slash-invoke when you want a specific one.

Invocation forms differ by harness. After setup, engine calls are always `stockroom <subcommand>` on PATH — see [CLI](../advanced/cli.md). Operational flags and recovery tables live in each skill’s `SKILL.md`; this page is only an index.

| Skill | Cursor | Claude Code | What it’s for |
| --- | --- | --- | --- |
| [`sr-dashboard`](#sr-dashboard) | `/sr-dashboard` | `/stockroom:sr-dashboard` | Open the local metrics UI |
| [`sr-initialize`](#sr-initialize) | `/sr-initialize` | `/stockroom:sr-initialize` | First-time / heal machine setup |
| [`sr-query`](#sr-query) | `/sr-query` | `/stockroom:sr-query` | Read-only SQL (structured lookups) |
| [`sr-search`](#sr-search) | `/sr-search` | `/stockroom:sr-search` | Default search (routes query / semantic) |
| [`sr-semantic`](#sr-semantic) | `/sr-semantic` | `/stockroom:sr-semantic` | Meaning-based (vector) search |

## `sr-dashboard`

Launches (or re-prints) the local read-only dashboard URL — use when you want the metrics UI, not a search answer.

→ [Dashboard](dashboard.md)

## `sr-initialize`

Walks a machine from “plugin installed” to “warehouse ready”: prerequisites, per-machine torch, on-path `stockroom` shim, optional nightly schedule, first ingest + embed. Idempotent — re-run anytime setup looks broken.

→ [Quickstart](quickstart.md) (get running) · [Load the Warehouse](ingest.md) (ingest / embed / schedule) · [Torch](troubleshooting/torch.md)

## `sr-query`

Read-only SQL against the warehouse for exact or structured lookups — ids, filters, counts, joins. Not for meaning-based recall.

→ [Search — `sr-query`](search.md#sr-query)

## `sr-search`

Friendly default when you are unsure whether the ask is structured SQL or meaning-based recall. Routes to `sr-query` and/or `sr-semantic` and synthesizes one answer.

→ [Search — `sr-search`](search.md#sr-search)

## `sr-semantic`

Vector search for content you can describe but not name exactly. Needs torch / embeddings; not for id filters or counts.

→ [Search — `sr-semantic`](search.md#sr-semantic)
