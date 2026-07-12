# Load the Warehouse

After [Quickstart](quickstart.md), your machine has a DuckDB warehouse and (usually) a first full load of data already in it.

This page is the mental model for how that warehouse stays current: **ingest** copies harness history in, **embed** turns message text into vectors for meaning-based search, and **scheduling** runs both on a nightly cadence so you are not babysitting freshness by hand.

Day-to-day search still goes through the agent (`sr-search` and friends). This page is for when you want to know what those pipelines do — or when you need to re-run them yourself.

## Ingest

Ingest is ETL from agentic coding harness transcript roots into the warehouse under stockroom home (`$STOCKROOM_HOME/warehouse.duckdb` — see [Installed layout](installed-layout.md)).

It writes harness-labeled rows into shared tables: `sessions`, `messages`, and `tool_calls`. Prompts and responses are stored whole; tool *inputs* are kept; tool *result* payloads are dropped. Thinking/reasoning blocks the harness keeps separate are not stored. Rows whose source transcripts later vanish are **not** pruned — the warehouse is allowed to outlive its sources.

**Default is incremental.** Stockroom remembers a per-harness watermark in `_sync_state` and only reads files past that point. Re-runs are cheap and safe.

```bash
stockroom ingest              # both harnesses, incremental
stockroom ingest --full       # ignore watermarks; re-read everything (still idempotent)
stockroom ingest --verbose    # progress lines (quiet by default)
```

`--harness cursor` or `--harness claude` limits to one source. Custom transcript roots and the optional Cursor enrichment DB are env overrides — see [Advanced > CLI](../advanced/cli.md).

`sr-initialize` runs `stockroom ingest --full` once so you are not waiting for the first nightly job. On years of history that first pass can many minutes (varying greatly depending on your machine's CPU and disk speed); it prints per-harness session/message/tool_call counts when done.

## Embed

Embed turns non-empty message text into local vectors ([BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), 384-dim, one row per chunk in `embeddings`). SQL query works without embeddings; **meaning-based recall does not.**

Embedding needs a working PyTorch install in the engine venv. Ingest does not. If embed or semantic search fails citing torch / the environment, fix torch first — [Troubleshooting >Torch](troubleshooting/torch.md).

**Default is incremental.** Only messages that still lack an embedding for the current model are processed. Re-runs resume cleanly after interruption.

```bash
stockroom embed              # pending messages only
stockroom embed --full       # re-embed all non-empty messages
stockroom embed --verbose
```

There must already be a warehouse (run ingest first). The first embed is the long pole: a large corpus on modest hardware can take hours, and the first run may also download the embedding model once if smoke testing during initialize did not already warm it. Nightly jobs stay cheap because they only catch up.

## Scheduling

Freshness is a nightly `stockroom ingest && stockroom embed` (incremental, not `--full`) on the platform scheduler — cron on Linux/WSL, launchd on macOS. Native Windows is not supported; use WSL. Output goes to `$STOCKROOM_HOME/logs/nightly.log`.

`sr-initialize` asks before installing the job. You can change the time, skip scheduling entirely, or manage it later:

```bash
stockroom schedule status
stockroom schedule install
stockroom schedule install --time 01:15
stockroom schedule remove
```

`install` is idempotent — it replaces Stockroom’s own entry, never duplicates it, and on cron it only touches a comment-delimited block. If `status` warns that the cron daemon is not running, the entry is written but will not fire until you start the daemon.

The optional schedule entry is also called out under [Installed layout](installed-layout.md). Session-start hooks never ingest or embed — they only heal the shim and launch the dashboard.

## Re-run and check coverage

When search feels stale, catch up incrementally first:

```bash
stockroom ingest
stockroom embed
```

If you skipped the first full load (or want to force a full re-read), use the same commands initialize used:

```bash
stockroom ingest --full
stockroom embed
```

Then sanity-check counts:

```bash
stockroom query "SELECT (SELECT count(*) FROM sessions) AS sessions, (SELECT count(*) FROM messages) AS messages, (SELECT count(*) FROM embeddings) AS embeddings"
```

Non-zero in all three columns means the warehouse is populated and searchable.

Stuck on empty results, staleness, or schedule? [Troubleshooting · Ingest](troubleshooting/index.md#ingest).
