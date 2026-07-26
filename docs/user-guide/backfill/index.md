# Backfill Legacy History

[Ingest](../ingest.md#ingest) reads the transcript roots a harness writes *today*. Some harnesses also left history behind in an older store that ingest does not read — history that is finite, does not grow, and is therefore worth excavating exactly once.

`stockroom backfill` is that excavation. It is a deliberate, human-run command: nothing schedules it, no hook fires it, and the nightly job stays `ingest && embed`.

## Sources

Each legacy store is a named **source**. Backfill runs every configured source by default.

| Source | Harness | What It Recovers | Page |
| --- | --- | --- | --- |
| `cursor-vscdb` | `cursor` | Cursor IDE "composer" conversations from before agent transcripts existed | [Cursor `state.vscdb`](cursor-vscdb.md) |

A source needs to be told where its store is; there are no discoverable defaults. A source with no configured path is reported and skipped so the others still run — naming it explicitly with `--source` makes it an error instead.

## The Required Sequence

!!! warning "Run these three steps in this order, every time"

	1. **Quit the harness completely.** Not just the window — the whole application.
	2. **`stockroom ingest`** — let ordinary ingest finish first.
	3. **`stockroom backfill`** — only now.

This is the procedure, not a suggestion. Each step exists because skipping it costs you something you will not be told about, and the two failures compound: an incomplete read *and* a warehouse that cannot tell you what you missed.

### Why Quit The Harness

A running harness holds its legacy store open and is still writing to it. Two things follow.

The read can tear. Backfill reports that cleanly and exits nonzero, so you will at least know.

The read can also be **quietly incomplete**, which is the dangerous one. On filesystems where stockroom must fall back to an immutable open — the WSL→Windows mount, most commonly — recent writes still sitting in the database's write-ahead log are invisible. Those conversations are not skipped, not counted, and not reported. They simply are not there, and the run exits 0 as though it were complete. Quitting the harness checkpoints that log so the whole store is readable.

Backfill is a run-once job against a corpus that never grows. A conversation missed by an unclean read stays missed until you happen to notice a gap in your own history and run it again.

### Why Ingest First

Backfill skips what the warehouse already holds. That skip set is a snapshot of what is *in* the warehouse right now, not a prediction of what ingest is about to add — so any conversation ingest has not caught up on yet is a live backfill candidate, even when a better copy of it is sitting in the transcript roots.

Nothing is lost when that happens: backfill never moves ingest's watermarks, so the next ingest still picks that transcript up and its higher-fidelity version replaces the reconstruction. But you pay for the overlap:

* **Embedding work, twice.** If `stockroom embed` runs in between, you embed the reconstruction, then ingest supersedes it and you embed the same conversations again. Backfill already creates a large embed backlog; this is the expensive mistake.
* **Numbers you cannot trust.** Conversations that were ingest's job get counted as backfill "written," so the summary stops telling you how much genuinely legacy-only history you actually recovered.

Running ingest first can only ever *enlarge* the skip set, and a larger skip set can never lose history. It also makes the backfill faster, because there is less to reconstruct.

## Running It

Once the harness is closed and ingest has finished:

```bash
stockroom backfill --dry-run              # rehearse: report only, writes nothing
stockroom backfill                        # every configured source
stockroom backfill --source cursor-vscdb  # just this one
stockroom backfill --verbose              # per-session progress (quiet by default)
```

`--dry-run` does everything a real run does — resolves each source, works out what is already present, reconstructs the rest — then reports what it would have written instead of writing it. It opens the warehouse read-only and takes no write lock, so it is safe to rehearse at any time. It does need a warehouse to compare against, and will tell you to run `stockroom ingest` first if there is not one.

Each run prints one line per source: sessions, messages, and tool calls written, out of how many candidates were found, and how many were skipped because they were already present or had nothing in them.

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
