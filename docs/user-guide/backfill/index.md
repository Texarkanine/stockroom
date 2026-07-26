# Backfill Legacy History

[Ingest](../ingest.md#ingest) reads the transcript roots a harness writes *today*. Some harnesses also left history behind in an older store that ingest does not read — history that is finite, does not grow, and is therefore worth excavating exactly once.

`stockroom backfill` is that excavation. It is a deliberate, human-run command: nothing schedules it, no hook fires it, and the nightly job stays `ingest && embed`.

## Sources

Each legacy store is a named **source**. Backfill runs every configured source by default.

| Source | Harness | What It Recovers | Page |
| --- | --- | --- | --- |
| `cursor-vscdb` | `cursor` | Cursor IDE "composer" conversations from before agent transcripts existed | [Cursor `state.vscdb`](cursor-vscdb.md) |

A source needs to be told where its store is; there are no discoverable defaults. A source with no configured path is reported and skipped so the others still run — naming it explicitly with `--source` makes it an error instead.

## Running It

Start with `--dry-run`. It does everything a real run does — resolves each source, works out what is already present, reconstructs the rest — and then reports what it would have written instead of writing it.

```bash
stockroom backfill --dry-run              # report only; writes nothing
stockroom backfill                        # every configured source
stockroom backfill --source cursor-vscdb  # just this one
stockroom backfill --verbose              # per-session progress (quiet by default)
```

Each run prints one line per source: sessions, messages, and tool calls written, out of how many candidates were found, and how many were skipped because they were already present or had nothing in them.

## What To Expect

* **Legacy stores are read strictly read-only.** Your harness's own state is never modified.
* **Re-running is safe.** Any session already in the warehouse is skipped, not overwritten — so an interrupted run is resumed simply by running it again.
* **Ingest is never disturbed.** Backfill reuses the same writer ordinary ingest uses, but it does not advance ingest's watermarks. Running it does not change what tonight's job will read.
* **Expect a long embed afterwards.** Backfill never embeds, and a large legacy store can substantially grow the message corpus. The next `stockroom embed` will therefore run far longer than usual — start it when you can leave it alone.
* **Close the harness first if you can.** Reading a store the harness is actively writing can yield a torn read. Backfill reports that in one line and exits nonzero rather than crashing, and you can simply re-run it later.

## Fixing A Run

Backfilled rows are exactly identifiable: `sessions.source_path` is the store they came from.

`--force` re-parses sessions **this same source** authored — the escape hatch for when a corrected parse needs to replace an earlier one:

```bash
stockroom backfill --source cursor-vscdb --force
```

It is deliberately narrow. Sessions ordinary ingest authored carry a transcript `source_path`, so they are never matched and never re-parsed, even under `--force`. Backfill cannot overwrite higher-fidelity history with its own reconstruction.

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
