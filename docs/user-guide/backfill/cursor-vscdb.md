# Cursor `state.vscdb`

Source name: **`cursor-vscdb`**. Harness: `cursor`.

Before Cursor wrote agent transcripts under `~/.cursor/projects`, IDE conversations ("composers") lived only inside Cursor's own key-value store, `globalStorage/state.vscdb`. Ordinary [ingest](../ingest.md#ingest) never reads that file. This source recovers those conversations.

The corpus is closed: Cursor no longer adds to it in a way ingest cannot see, so this is a run-once job.

!!! warning "Quit Cursor, then ingest, then backfill"

	The [required sequence](index.md#the-required-sequence) is not optional for this source, and this is the source it was written for. Cursor holds `state.vscdb` open while it runs, and on a WSL→Windows mount an open Cursor makes recent conversations **silently invisible** to the run — not skipped, not counted, not reported.

## Pointing At The Store

There is no discoverable default. Under WSL the database lives on the Windows side of the mount, and there is no reliable way to guess which Windows user profile is yours — so the path is always explicit. Three ways, highest precedence first:

```bash
# 1. flag
stockroom backfill --state-vscdb "/mnt/c/Users/you/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"

# 2. environment
STOCKROOM_CURSOR_STATE_VSCDB=/path/to/state.vscdb stockroom backfill
```

```toml
# 3. config — $XDG_CONFIG_HOME/stockroom/config.toml (or ~/.config/stockroom/config.toml)
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

Stockroom prefers SQLite's read-only mode, and falls back to an *immutable* open on filesystems where read-only mode cannot take its locks (the WSL→Windows 9p mount is the common case). An immutable open cannot see writes still sitting in the write-ahead log. **This is why Cursor has to be closed**, and why it matters more than it sounds: those conversations do not fail, they are simply not seen, and the run reports success without them. Quitting Cursor checkpoints the log into the database proper, which is what makes the store fully readable.

A store being actively written by a running Cursor can also produce a torn read. That failure at least announces itself — backfill reports it in one line and exits nonzero.

The database can be several gigabytes. Backfill reads one conversation at a time using indexed key ranges rather than loading it whole, so memory stays flat and a slow mount stays tolerable.

## What Lands In The Warehouse

| Column | Value |
| --- | --- |
| `harness` | `cursor` |
| `session_id` | The composer id |
| `entrypoint` | `ide` — these are genuinely IDE conversations |
| `source_path` | The `state.vscdb` path, which is what makes a run identifiable and reversible |
| `project_id` | Cursor's own workspace id |
| `cwd` | The workspace folder, when Cursor's workspace storage still records it |

Composer ids share a namespace with agent-transcript session ids. That is what makes "skip what is already present" exact rather than a guess — and it is why running [ingest first](index.md#why-ingest-first) is worth the wait: every conversation ingest has already claimed is one this source will correctly leave alone. Should the two overlap anyway, a later ingest supersedes the reconstruction rather than duplicating it; you just pay to embed the same conversation twice.

Because `cwd` is recovered, backfilled sessions land in the same workspace grouping as ordinary transcript sessions for the same project. They show up alongside the rest of that project's history in the [dashboard](../dashboard.md) and in search.

### What Is Left Out

* **Empty drafts.** A composer you opened and never used has nothing to reconstruct; it is counted and skipped.
* **Thinking and reasoning blocks**, as everywhere else in stockroom — they are never stored.
* **Tool results.** Tool *inputs* are kept whole; result payloads are dropped, matching ingest.
* **Timestamps Cursor never recorded.** A composer with no recoverable times keeps NULL `started_at`, which means it is honestly absent from time-windowed dashboard metrics rather than being parked on today's date. Its messages are still fully searchable.

### Token Counts

Where Cursor recorded per-turn token usage, it is stored on the individual message that reported it, and `session_token_usage` rolls it up with `token_grain = 'message'` — the same semantics as Claude Code's per-message usage. Turns Cursor did not meter stay NULL rather than being written as zero, because a zero would claim the turn cost nothing.

Conversations from before Cursor recorded usage at all simply report `token_grain = 'none'`, which is also what ordinary Cursor ingest reports.

## Undoing It

See [Undoing A Run](index.md#undoing-a-run) — delete by the `state.vscdb` path in `sessions.source_path`.
