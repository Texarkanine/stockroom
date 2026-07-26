# Backfill

Backfill is one-shot excavation of a harness's *legacy* store — history that predates the transcript roots [ingest](warehouse.md) reads, is finite, and does not grow. It is a sibling of the ingest pipeline, not a mode of it, and the separation is structural rather than conventional.

Operator how-to lives in [User Guide → Backfill Legacy History](../user-guide/backfill/index.md). This page is why it is shaped the way it is.

## Not On Any Automatic Path

`stockroom backfill` is human-run, always. No session-start hook invokes it, the scheduler entry stays exactly `stockroom ingest && stockroom embed`, and nothing reachable from the nightly path imports the `backfill` package.

That last one is the load-bearing guarantee, and it is an *absence*, so it is asserted rather than assumed: guard tests fail if the rendered schedule payload gains a `backfill` token, or if the `stockroom.ingest` package acquires an import edge onto `stockroom.backfill`. Legacy-store reads stay one deliberate command away from the thing that runs unattended every night.

```mermaid
flowchart LR
    subgraph nightly["Nightly (automatic)"]
        Sched[schedule] --> Ing[ingest] --> Emb[embed]
    end
    subgraph oneshot["Backfill (human-run, one-shot)"]
        Human([Human]) --> BF[backfill]
    end
    Roots[(transcript roots)] --> Ing
    Legacy[(legacy store)] --> BF
    Ing --> W[[ingest.writer]]
    BF --> W
    W --> WH[(warehouse)]
    Ing --> SS[_sync_state watermarks]
    BF -.->|never| SS
```

## Orchestrator Over Adapters

Backfill is cross-harness by construction, even though exactly one legacy store is known today. The package mirrors how ingest is an orchestrator plus per-harness parsers:

| Module | Role |
| --- | --- |
| `backfill/__init__.py` | Source registry, skip set, write loop, per-source summary |
| `backfill/cursor_vscdb.py` | Today's only adapter |
| `backfill/__main__.py` | CLI |

Adapters own their source format and nothing else — they read their store, resolve their own path from flag/env/config, and yield the same `NormalizedSession` objects ingest parsers yield. **The orchestrator owns every warehouse interaction**; no adapter is handed a connection, and a test asserts a run still writes when the adapter never sees one. A second legacy store is a new file plus a registry entry, not orchestrator surgery.

The contract and how to add one: [Contributing → Backfill Adapters](../contributing/backfill-adapters.md).

## Reuses The Writer, Never The Watermark

Backfill writes through `ingest.writer.write_session` — the same single SQL touchpoint for session persistence that ingest uses — so backfilled rows are shaped, keyed, and de-duplicated identically. `workspace_key` in particular is derived by the writer, which is what lets a backfilled session converge with a transcript-authored session for the same working directory.

It deliberately never calls `update_watermark`. A run leaves `_sync_state` exactly as it found it, so excavating history does not change what tonight's incremental ingest will read.

## Never Clobbering What It Did Not Write

The writer persists idempotently by delete-then-insert on `(harness, session_id)`, which makes a wrong skip set actively destructive rather than merely wasteful. Two things contain that:

**Provenance is exact.** Backfilled sessions carry `entrypoint = 'ide'` and a `source_path` naming the legacy store. `entrypoint` still means *surface*, so no third value was invented for it; `source_path` is what makes a run identifiable, correctable, and reversible.

**The default skip set is everything already present.** Any `session_id` already in the warehouse for the adapter's harness is skipped before parsing, not after — adapters enumerate candidate ids cheaply first, so the expensive parse only runs on what will actually be written. A test asserts a skipped row is byte-identical afterwards.

`--force` narrows that skip set to sessions whose `source_path` is *this adapter's own store*, so a corrected parse can replace its own earlier output without hand-written SQL. Transcript-authored rows carry a transcript `source_path` and are therefore unmatchable even under force. The escape hatch is one predicate rather than a bookkeeping column precisely because provenance was decided first.

## Reading Foreign Stores Safely

A legacy store belongs to the harness, which may be running. Adapters open it strictly read-only and are expected to fail soft: an absent, unreadable, or actively-written store yields a one-line message and a nonzero exit, never a traceback. One unparseable record does not abort a run, and one failed source does not stop the others.

Source-specific consequences of that — the read-mode ladder, what an immutable open cannot see — belong on the adapter's own page: [Cursor `state.vscdb`](../user-guide/backfill/cursor-vscdb.md#how-it-reads).

## Grain And Honesty

Two conventions matter enough to state as architecture, because both are places where a plausible convenience would have corrupted a column's meaning.

**Tokens are stored at the grain the source reports.** A per-turn count lands on *that* message, and session `*_tokens` stay NULL so `session_token_usage` reports `token_grain = 'message'`. Summing message counts into the session columns is explicitly forbidden by migration `0007`, and would additionally make the rollup view mislabel the grain as `'session'`.

**`source_mtime` stays NULL for a shared store.** The column means "the mtime of *this conversation's* source transcript" — a per-conversation activity proxy that works only because ingest reads one file per conversation. A legacy store is one file holding thousands of conversations, so its mtime is approximately the run time and says nothing about any of them. Writing it would place every timeless conversation on today's date in the dashboard's `COALESCE(started_at, source_mtime)` window, fabricating exactly the activity a backfill exists to recover honestly.

That left `source_mtime`'s other, quieter job — seeding `messages.first_seen_at`, which means "when stockroom first observed this message" and is [not rebuildable from sources](warehouse.md). The two meanings are decoupled in the writer: `first_seen_at` falls back to the run clock when `source_mtime` is absent. Inert for every current parser, since they all set `source_mtime`, and it closes a latent gap where any parser omitting it silently discarded observation time forever.
