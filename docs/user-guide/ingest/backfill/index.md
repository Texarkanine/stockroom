# Backfill Legacy History

[Ingest](../ingest.md#ingest) reads the transcript roots a harness writes *today*. Some harnesses also left history behind in an older store that ingest does not read — history that is finite, does not grow, and is therefore worth excavating exactly once.

`stockroom backfill` is that excavation. It is a deliberate, one-off command not intended to be scheduled.

## Sources

Each legacy store is a named **source**. Backfill runs every configured source by default.

| Source (type) | Harness | What It Recovers | Page |
| --- | --- | --- | --- |
| `cursor-vscdb` | `cursor` | Cursor IDE "composer" conversations from before agent transcripts existed | [Cursor `state.vscdb`](cursor-vscdb.md) |

A source needs to be told where its store is; there are no discoverable defaults. A source with no configured path is reported and skipped so the others still run — naming it explicitly with `--source` makes it an error instead.

## The Required Sequence

!!! warning "Run these three steps in this order, every time"

1. **Quit the harness completely.** Not just the window — the whole application.
2. **`stockroom ingest`** — let ordinary ingest finish first.
3. **`stockroom backfill`** — only now.

### Why Quit The Harness

A running harness may hold its legacy store open and is still writing to it. Two things follow.

1. The read can be "torn" — meaning the file was modified during the read, resulting in an inconsistent or incomplete snapshot.
2. The read can also be **quietly incomplete**. If the store is open and active, recent writes may not have been committed to the store - they'll just be missed.

Backfill is supposed to be a one-off command against an old corpus that never grows. Ensure the store's not open and can't grow mid-backfill.

### Why Ingest First

Backfill skips what the warehouse already holds - what `ingest` has already loaded.

Any conversation ingest has not caught up on yet is a live `backfill` candidate, even when a better copy of it is sitting in the transcript roots.

Nothing is lost when that happens: `backfill` never moves `ingest`'s watermarks, so the next `ingest` still picks that transcript up and its higher-fidelity version replaces the reconstruction. But you pay for the overlap:

* **Embedding work, twice.** If `stockroom embed` runs in between, you embed the reconstruction, then ingest supersedes it and you embed the same conversations again.
* **Numbers you cannot trust.** Conversations that were ingest's job get counted as backfill "written," so the summary stops telling you how much genuinely legacy-only history you actually recovered.

Running ingest first can only ever *enlarge* the skip set, and a larger skip set can never lose history. It also makes the backfill faster, because there is less to reconstruct.

### Why is This Even a Problem?

Cursor's [state.vscdb](cursor-vscdb.md) is one instance of this risk profile:

Historically, conversations were tracked in there.
Recently, conversation transcripts - richer ones - are tracked elsewhere, and that new location is what `ingest` targets. But new conversations are *still* written to the old location in the old format.

If Cursor is open, the backfill data source is still being written to.

If you don't ingest first, your brand-new Cursor sessions get ingested through `backfill` - without rich data - and then again during `ingest` - with the richer data.

## Running It

Once the harness is closed and ingest has finished:

```bash
stockroom backfill --dry-run  # rehearse: report only, writes nothing
stockroom backfill --verbose  # all sources w/ progress
```

`--dry-run` does everything a real run does — resolves each source, works out what is already present, reconstructs the rest — then reports what it would have written instead of writing it. It opens the warehouse read-only and takes no write lock, so it is safe to rehearse at any time. It does need a warehouse to compare against, and will tell you to run `stockroom ingest` first if there is not one.

Afterwards, embed:

```bash
stockroom embed
```

## What To Expect

* **Legacy stores are read strictly read-only.** Your harness's own state is never modified.
* **Re-running is safe.** Any session already in the warehouse is skipped, not overwritten — so an interrupted run is resumed simply by running it again.
* **Ingest is never disturbed.** Backfill reuses the same writer ordinary ingest uses, but it does not advance ingest's watermarks. Running it does not change what tonight's job will read.
* **Expect a long embed afterwards.** Backfill never embeds, and a large legacy store can substantially grow the message corpus. The `stockroom embed` that follows will therefore run far longer than usual — start it when you can leave it alone.

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

`stockroom query` opens the warehouse read-only, so the deletion itself needs a [DuckDB client](../../advanced/duckdb.md) — with nothing else holding the warehouse open:

```sql
CREATE TEMP TABLE doomed AS
  SELECT harness, session_id FROM sessions WHERE source_path = '/path/to/store';
DELETE FROM tool_calls  WHERE (harness, session_id) IN (SELECT * FROM doomed);
DELETE FROM messages    WHERE (harness, session_id) IN (SELECT * FROM doomed);
DELETE FROM sessions    WHERE (harness, session_id) IN (SELECT * FROM doomed);
```

All three tables are needed — the warehouse has no foreign keys, so nothing cascades. Any embeddings those messages owned are pruned by the next `stockroom embed`.

## Where Next?

* Per-source setup and caveats: [Cursor `state.vscdb`](cursor-vscdb.md)
* Why backfill sits outside every automatic path: [Architecture → Backfill](../../architecture/backfill.md)
* Adding a source: [Contributing → Backfill Adapters](../../contributing/backfill-adapters.md)
