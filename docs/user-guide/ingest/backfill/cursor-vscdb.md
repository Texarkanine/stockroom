# Cursor `state.vscdb`

| Source Name         | Harness  |
|---------------------|----------|
| **`cursor-vscdb`**  | `cursor` |

Before Cursor wrote agent transcripts under `~/.cursor/projects`, IDE conversations ("composers") lived only inside Cursor's own key-value store, `globalStorage/state.vscdb`. Ordinary [ingest](../ingest.md#ingest) never reads that file. This source recovers those conversations.

## Pointing At The Store

There is no discoverable default. In priority order:

1. Flag:
	```bash
	stockroom backfill --state-vscdb "/mnt/c/Users/you/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
	```
2. Environment variable:
	```bash
	STOCKROOM_CURSOR_STATE_VSCDB=/path/to/state.vscdb stockroom backfill
	```
3. Config file:
	`$XDG_CONFIG_HOME/stockroom/config.toml` (or `~/.config/stockroom/config.toml` by default): 
	```toml
	[cursor]
	state_vscdb = "/mnt/c/Users/you/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
	```

Typical locations of `globalStorage`:

| Platform | Path |
| --- | --- |
| Linux | `~/.config/Cursor/User/globalStorage/state.vscdb` |
| macOS | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |
| Windows | `%APPDATA%\Cursor\User\globalStorage\state.vscdb` |
| WSL → Windows | `/mnt/c/Users/<you>/AppData/Roaming/Cursor/User/globalStorage/state.vscdb` |

Config is the right home if you expect to re-run; the flag is for one-offs.

## How It Reads

The database is opened **strictly read-only** — your Cursor state is never modified.

<!-- TODO: this is architecture
Stockroom prefers SQLite's read-only mode, and falls back to an *immutable* open on filesystems where read-only mode cannot take its locks (the WSL→Windows 9p mount is the common case). An immutable open cannot see writes still sitting in the write-ahead log. **This is why Cursor has to be closed**, and why it matters more than it sounds: those conversations do not fail, they are simply not seen, and the run reports success without them. Quitting Cursor checkpoints the log into the database proper, which is what makes the store fully readable.

A store being actively written by a running Cursor can also produce a torn read. That failure at least announces itself — backfill reports it in one line and exits nonzero.

The database can be several gigabytes. Backfill reads one conversation at a time using indexed key ranges rather than loading it whole, so memory stays flat and a slow mount stays tolerable.
-->

## What Lands In The Warehouse

| Column | Value |
| --- | --- |
| `harness` | `cursor` |
| `session_id` | The composer id |
| `entrypoint` | `ide` — these are genuinely IDE conversations |
| `source_path` | The `state.vscdb` path, which is what makes a run identifiable and reversible |
| `project_id` | Cursor's own workspace id |
| `cwd` | The workspace folder, when Cursor's workspace storage still records it |
| `models` | Every model the conversation used |
| `messages.model` | The model that produced that turn, where Cursor recorded it |

Composer ids share a namespace with agent-transcript session ids; this is how backfill can skip existing sessions, and how `ingest` can "take over" any recent sessions that you accidentally backfill.

Because `cwd` is recovered, backfilled sessions land in the same workspace grouping as ordinary transcript sessions for the same project. They show up alongside the rest of that project's history in the [dashboard](../dashboard.md) and in search.

### What Is Left Out

* **Empty drafts.** A composer you opened and never used has nothing to reconstruct; it is counted and skipped.
* **Thinking and reasoning blocks**, as everywhere else in stockroom — they are never stored.
* **Tool results.** Tool *inputs* are kept whole; result payloads are dropped, matching ingest.
* **Timestamps Cursor never recorded.** A composer with no recoverable times keeps NULL `started_at`, which means it is honestly absent from time-windowed dashboard metrics rather than being parked on today's date. Its messages are still fully searchable.

### Model Attribution

Backfill keeps both session and per-message models — ordinary Cursor ingest only gets session models from the recent `ai-code-tracking` sidecar, so older history is often blank.

`sessions.models` lists every model used, in order. `messages.model` is sparse: Cursor stamps it on choose/change, not every turn. Literal `default` is stored as written.

### Token Counts

Per-turn usage lands on that message; the warehouse's [`session_token_usage`](../../../architecture/warehouse.md#dual-grain-token-usage) VIEW rolls it up with `token_grain = 'message'`. Unmetered turns stay NULL (not zero). Pre-usage conversations get `token_grain = 'none'`, same as ordinary ingest.
