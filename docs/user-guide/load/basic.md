
# Ingest & Embed

When search feels stale, catch up:

```bash
stockroom ingest
stockroom embed
```

That is the day-to-day loop. **Ingest** copies harness history into the warehouse; **embed** turns message text into vectors for meaning-based search; a **nightly schedule** runs both so you are not babysitting freshness by hand.

Day-to-day search still goes through the agent (`sr-search` and friends). This page is for when you want to know what those pipelines do — or when you need to re-run them yourself.

## Ingest

Ingest is ETL from agentic coding harness transcript roots into the warehouse under stockroom home (`$STOCKROOM_HOME/warehouse.duckdb` — see [Installed layout](../installed-layout.md)).

It writes harness-labeled rows into shared tables: `sessions`, `messages`, and `tool_calls`. Prompts and responses are stored whole; tool *inputs* are kept; tool *result* payloads are dropped. Thinking/reasoning blocks the harness keeps separate are not stored. Rows whose source transcripts later vanish are **not** pruned — the warehouse is allowed to outlive its sources.

**Default is incremental.** Stockroom remembers a per-`(harness, source_root)` watermark in `_sync_state` and only reads files past that point. Cursor therefore tracks projects and chats roots independently. Re-runs are cheap and safe. 

**Migrations do not Backfill.** Structural migrations do not backfill columns such as `entrypoint` — use `stockroom ingest --full` after a database schema upgrade if you want older rows repopulated from sources (this will be infrequent).

## Embed

Embed turns non-empty message text into local vectors ([BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), 384-dim, one row per chunk in `embeddings`). SQL query works without embeddings; **meaning-based recall does not.**

Embedding needs a working PyTorch install in the engine venv. Ingest does not. If embed or semantic search fails citing torch / the environment, fix torch first — [Troubleshooting > Torch](../troubleshooting/torch.md).

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

`install` is idempotent — it replaces Stockroom's own entry, never duplicates it, and on cron it only touches a comment-delimited block. If `status` warns that the cron daemon is not running, the entry is written but will not fire until you start the daemon.

The optional schedule entry is also called out under [Installed layout](../installed-layout.md). Session-start hooks never ingest or embed — they only heal the shim and launch the dashboard.


## Re-run and Check Coverage

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
