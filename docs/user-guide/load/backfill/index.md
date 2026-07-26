# Backfill Legacy History

`stockroom backfill` excavates finite legacy stores that ordinary [ingest](../index.md#ingest) never reads. Run it deliberately, once, if you know you need it. Backfill is not and should not be scheduled.

## The Required Sequence

!!! warning "Run these four steps in this order, every time"

1. **Quit the harness completely.** Not just the window — all instance of the whole application.
2. **`stockroom ingest`** — let ordinary ingest finish first.
3. **`stockroom backfill`**
4. **`stockroom embed`** — backfill never embeds; semantic search needs this after.

**Why quit:** a running harness can tear the read or leave recent writes invisible — backfill may exit 0 having silently missed conversations.

**Why ingest first:** backfill skips what the warehouse already holds. Skipping ingest may pull in live sessions that ingest would have done better, wastes embed work when those rows get superseded, and may corrupt the "written" summary as a measure of legacy-only recovery.

## Sources

Each legacy store is a named **source**. Backfill runs every configured source by default.

| Source (type) | Harness | What It Recovers | Page |
| --- | --- | --- | --- |
| `cursor-vscdb` | `cursor` | Cursor IDE "composer" conversations from before agent transcripts existed | [Cursor `state.vscdb`](cursor-vscdb.md) |

A source needs to be told where its store is; there are no discoverable defaults. A source with no configured path is reported and skipped so the others still run — naming it explicitly with `--source` makes it an error instead.

## Running It

Once the harness is closed and ingest has finished:

```bash
stockroom backfill            # the run
stockroom backfill --dry-run  # rehearse: report only, writes nothing
stockroom backfill --verbose  # all sources w/ progress
```

`--dry-run` does everything a real run does — resolves each source, works out what is already present, reconstructs the rest — then reports what it would have written instead of writing it. It opens the warehouse read-only and takes no write lock, so it is safe to rehearse at any time. It does need a warehouse to compare against, and will tell you to run `stockroom ingest` first if there is not one.

## What To Expect

* **Legacy stores are read strictly read-only.** Your harness's own state is never modified.
* **Re-running is safe.** Any session already in the warehouse is skipped, not overwritten — so an interrupted run is resumed simply by running it again.
* **Ingest is never disturbed.** Backfill reuses the same writer ordinary ingest uses, but it does not advance ingest's watermarks. Running it does not change what tonight's job will read.
* **Expect a long embed afterwards.** A large legacy store can substantially grow the message corpus. Start `stockroom embed` when you can leave it alone.

## Fixing A Run

Backfilled rows are exactly identifiable: `sessions.source_path` is the store they came from.

`--force` re-parses sessions **this same source** authored — the escape hatch for when a corrected parse needs to replace an earlier one:

```bash
stockroom backfill --source cursor-vscdb --force
```

It is deliberately narrow. Sessions ordinary ingest authored carry a transcript `source_path`, so they are never matched and never re-parsed, even under `--force`. Backfill cannot overwrite higher-fidelity history with its own reconstruction.

!!! warning "Always embed after a `--force` run"
	Message IDs are positional (`{session_id}#{ordinal}`), so a corrected parse that keeps or drops a different set of messages renumbers everything after the change. Those messages' embeddings are dropped as stale, and only `stockroom embed` puts them back — until it runs, the re-parsed conversations are missing from semantic search.

## Undoing A Run

Delete by the same `source_path`. Count first:

```bash
stockroom query "SELECT count(*) FROM sessions WHERE source_path = '/path/to/store'"
```

`stockroom query` opens the warehouse read-only, so the deletion itself needs a [DuckDB client](../../../advanced/duckdb.md) — with nothing else holding the warehouse open:

```sql
CREATE TEMP TABLE doomed AS
  SELECT harness, session_id FROM sessions WHERE source_path = '/path/to/store';
DELETE FROM tool_calls  WHERE (harness, session_id) IN (SELECT * FROM doomed);
DELETE FROM messages    WHERE (harness, session_id) IN (SELECT * FROM doomed);
DELETE FROM sessions    WHERE (harness, session_id) IN (SELECT * FROM doomed);
```

All three tables are needed — the warehouse has no foreign keys, so nothing cascades. Any embeddings those messages owned are pruned by the next `stockroom embed`.
