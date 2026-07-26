# Cursor `state.vscdb`

| Source Name         | Harness  |
|---------------------|----------|
| **`cursor-vscdb`**  | `cursor` |

Before Cursor wrote agent transcripts under `~/.cursor/projects`, IDE conversations ("composers") lived only inside Cursor's own key-value store, `globalStorage/state.vscdb`. Ordinary [ingest](../basic.md#ingest) never reads that file. This source recovers those conversations.

## Pointing At The Store

There is no discoverable default. **Put the path in config** if you expect to re-run:

`$XDG_CONFIG_HOME/stockroom/config.toml` (or `~/.config/stockroom/config.toml` by default):

```toml
[cursor]
state_vscdb = "/mnt/c/Users/you/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
```

Typical locations:

| Platform | Path |
| --- | --- |
| Linux | `~/.config/Cursor/User/globalStorage/state.vscdb` |
| macOS | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |
| Windows | `%APPDATA%\Cursor\User\globalStorage/state.vscdb` |
| WSL → Windows | `/mnt/c/Users/<you>/AppData/Roaming/Cursor/User/globalStorage/state.vscdb` |

Alternatives for one-offs (same path, different injection):

1. Flag: `stockroom backfill --state-vscdb "/path/to/state.vscdb"`
2. Environment: `STOCKROOM_CURSOR_STATE_VSCDB=/path/to/state.vscdb stockroom backfill`

Priority when more than one is set: flag → environment → config.

## How It Reads

The database is opened **strictly read-only** — your Cursor state is never modified.

**If Cursor is open, backfill can exit 0 and silently miss conversations.** An immutable open (needed on some mounts, including WSL→Windows) cannot see the write-ahead log; quitting Cursor checkpoints that log into the database. A torn read from a live writer announces itself and exits nonzero — the silent miss does not.

The database can be several gigabytes. Backfill reads one conversation at a time, so memory stays flat on a slow mount.

## What Lands In The Warehouse

| Column | Value |
| --- | --- |
| `harness` | `cursor` |
| `session_id` | The composer id |
| `entrypoint` | `ide` — these are genuinely IDE conversations |
| `source_path` | The `state.vscdb` path, which is what makes a run identifiable and reversible |
| `project_id` | Cursor's own workspace id |
| `cwd` | The workspace folder, when Cursor's workspace storage still records it |
| `models` | Models Cursor recorded for the conversation (may be empty) |
| `messages.model` | The model that produced that turn, where Cursor recorded it |

Composer ids share a namespace with agent-transcript session ids; this is how backfill can skip existing sessions, and how `ingest` can take over any recent sessions that you accidentally backfill.

Because `cwd` is recovered, backfilled sessions land in the same workspace grouping as ordinary transcript sessions for the same project. They show up alongside the rest of that project's history in the [dashboard](../../dashboard.md) and in search.

### What Is Left Out

* **Empty drafts.** A composer you opened and never used has nothing to reconstruct; it is counted and skipped.
* **Thinking and reasoning blocks**, as everywhere else in stockroom — they are never stored.
* **Tool results.** Tool *inputs* are kept whole; result payloads are dropped, matching ingest.
* **Timestamps Cursor never recorded.** A composer with no recoverable times keeps NULL `started_at`, which means it is honestly absent from time-windowed dashboard metrics rather than being parked on today's date. Its messages are still fully searchable.

## Reference

**Models.** Backfill keeps both session and per-message models — ordinary Cursor ingest only gets session models from the recent `ai-code-tracking` sidecar, so older history is often blank. `sessions.models` lists every model used, in order. `messages.model` is sparse: Cursor stamps it on choose/change, not every turn. Literal `default` is stored as written.

**Tokens.** Per-turn usage lands on that message; the warehouse's [`session_token_usage`](../../../architecture/warehouse.md#dual-grain-token-usage) VIEW rolls it up with `token_grain = 'message'`. Unmetered turns stay NULL (not zero). Pre-usage conversations get `token_grain = 'none'`, same as ordinary ingest.
