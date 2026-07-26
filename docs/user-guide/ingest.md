# Load the Warehouse

After [Quickstart](quickstart.md), your machine has a DuckDB warehouse and (usually) a first full load of data already in it.

This page is the mental model for how that warehouse stays current: **ingest** copies harness history in, **embed** turns message text into vectors for meaning-based search, and **scheduling** runs both on a nightly cadence so you are not babysitting freshness by hand.

Day-to-day search still goes through the agent (`sr-search` and friends). This page is for when you want to know what those pipelines do — or when you need to re-run them yourself.

## Ingest

Ingest is ETL from agentic coding harness transcript roots into the warehouse under stockroom home (`$STOCKROOM_HOME/warehouse.duckdb` — see [Installed layout](installed-layout.md)).

It writes harness-labeled rows into shared tables: `sessions`, `messages`, and `tool_calls`. Prompts and responses are stored whole; tool *inputs* are kept; tool *result* payloads are dropped. Thinking/reasoning blocks the harness keeps separate are not stored. Rows whose source transcripts later vanish are **not** pruned — the warehouse is allowed to outlive its sources.

**Default is incremental.** Stockroom remembers a per-`(harness, source_root)` watermark in `_sync_state` and only reads files past that point. Cursor therefore tracks projects and chats roots independently. Re-runs are cheap and safe. Structural migrations do not backfill columns such as `entrypoint` — use `stockroom ingest --full` after an upgrade if you want older rows repopulated from sources.

Cursor Agent CLI chats (`~/.cursor/chats/**/store.db`) are parsed best-effort: if a store is locked, corrupt, or its internal blob layout drifts, that session is skipped and the rest of the ingest continues (the chats watermark does not advance past a skipped store, so a later run can retry). Empty or meta-only stores still upsert a session with zero messages. Fixture tests in the repo fail loudly when the known layout changes — operators should not expect a hard ingest failure from layout drift alone.

```bash
stockroom ingest              # both harnesses, incremental
stockroom ingest --full       # ignore watermarks; re-read everything (still idempotent)
stockroom ingest --verbose    # progress lines (quiet by default)
```

`--harness cursor` or `--harness claude` limits to one source. Non-default transcript roots are env overrides on the same command:

```bash
STOCKROOM_CURSOR_ROOT=/path/to/cursor/projects stockroom ingest
STOCKROOM_CURSOR_CHATS_ROOT=/path/to/cursor/chats stockroom ingest
STOCKROOM_CLAUDE_ROOT=/path/to/claude/projects stockroom ingest
```

Defaults are `~/.cursor/projects`, `~/.cursor/chats`, and `~/.claude/projects`.

`sr-initialize` runs `stockroom ingest --full` once so you are not waiting for the first nightly job. On years of history that first pass can take many minutes (varying greatly depending on your machine's CPU and disk speed); it prints per-harness session/message/tool_call counts when done.

### Cursor `sessions.models` Enrichment

Cursor has no in-band session model grain. When available, ingest fills `sessions.models` from Cursor's optional `ai-code-tracking.db` sidecar(s).

**Default ingest walks and merges every readable candidate:**

* Linux/Mac paths under `~/.cursor/`
* WSL Windows-home mounts under `/mnt/<drive>/Users/*/.cursor/...`

Optional **additive** pins (if you've got a weird setup) live in XDG config — `$XDG_CONFIG_HOME/stockroom/config.toml` or `~/.config/stockroom/config.toml`:

```toml
[cursor]
ai_tracking_dbs = [
  "/some/funky/path/.cursor/ai-tracking/ai-code-tracking.db",
]
```

Pins are unioned with discovery (not a replacement). Missing pins fail soft.

For tests or one-shots, `STOCKROOM_AI_TRACKING_DB` forces a **single** DB and disables the multi-path walk:

```bash
STOCKROOM_AI_TRACKING_DB=/path/to/ai-code-tracking.db stockroom ingest
```

## Backfill legacy history

Ingest reads the transcript roots a harness writes *today*. Some harnesses also left history behind in an older store that ingest does not read — history that is finite, does not grow, and is therefore worth excavating exactly once.

`stockroom backfill` is that excavation. It is **never scheduled** (the nightly entry stays `ingest && embed`), and it is safe to re-run: any session already in the warehouse is skipped rather than overwritten.

| Source | Harness | What it recovers | Where it reads |
| --- | --- | --- | --- |
| `cursor-vscdb` | `cursor` | Cursor IDE "composer" conversations from before agent transcripts existed | Cursor's `globalStorage/state.vscdb` |

```bash
stockroom backfill --dry-run    # report what would be written, write nothing
stockroom backfill              # every configured source
stockroom backfill --source cursor-vscdb --verbose
```

### Pointing at the Cursor store

There is no discoverable default — on WSL the database lives on the Windows side — so the path is always explicit, by flag, env var, or config:

```bash
stockroom backfill --state-vscdb "/mnt/c/Users/you/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
STOCKROOM_CURSOR_STATE_VSCDB=/path/to/state.vscdb stockroom backfill
```

```toml
[cursor]
state_vscdb = "/mnt/c/Users/you/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
```

A source with no configured path is reported and skipped so the other sources still run; naming it explicitly with `--source` makes it an error instead.

### What to expect

* **The database is read strictly read-only.** Your Cursor state is never modified. On mounts that do not support SQLite's locking (WSL→Windows), stockroom falls back to an immutable open, which cannot see the newest un-checkpointed writes. That tail is current activity, which ordinary ingest already covers.
* **Close Cursor first if you can.** Reading a database a running Cursor is writing can yield a torn read; backfill reports it and exits nonzero rather than crashing.
* **Expect a long embed afterwards.** Backfill can roughly double the message corpus, and it never embeds. The next `stockroom embed` therefore runs far longer than usual — run it when you can leave it alone.
* **Empty drafts are skipped.** A composer with no reconstructable messages is counted and not written.

### Fixing or undoing a run

Backfilled rows are exactly identifiable: their `sessions.source_path` is the store they came from.

`--force` re-parses sessions **this same source** authored — the escape hatch for when a corrected parse needs to replace an earlier one. Sessions ordinary ingest authored carry a transcript `source_path` and stay untouched even under `--force`.

To undo a run entirely, delete by that path. `stockroom query` is read-only, so this needs a DuckDB client against `$STOCKROOM_HOME/warehouse.duckdb` — with nothing else holding the warehouse open:

```sql
CREATE TEMP TABLE doomed AS
  SELECT harness, session_id FROM sessions WHERE source_path = '/path/to/state.vscdb';
DELETE FROM tool_calls  WHERE (harness, session_id) IN (SELECT * FROM doomed);
DELETE FROM messages    WHERE (harness, session_id) IN (SELECT * FROM doomed);
DELETE FROM sessions    WHERE (harness, session_id) IN (SELECT * FROM doomed);
```

Check the count first with `stockroom query "SELECT count(*) FROM sessions WHERE source_path = '/path/to/state.vscdb'"`. Any embeddings those messages owned are pruned by the next `stockroom embed`.

## Embed

Embed turns non-empty message text into local vectors ([BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), 384-dim, one row per chunk in `embeddings`). SQL query works without embeddings; **meaning-based recall does not.**

Embedding needs a working PyTorch install in the engine venv. Ingest does not. If embed or semantic search fails citing torch / the environment, fix torch first — [Troubleshooting > Torch](troubleshooting/torch.md).

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
