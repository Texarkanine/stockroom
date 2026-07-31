# Lifecycle

When Stockroom work runs on a live machine: hooks, the nightly schedule, and the dashboard process. This is *when* things fire — not how to install or how to write SQL.

## Session-start hooks

Constraints on the hook, and what it actually runs. Heavy ETL does not belong here — see [Scheduled ingest and embed](#scheduled-ingest-and-embed).

### Hook doctrine

Harness session-start hooks are designed to be:

- **Fire-and-forget** — stdout/stderr discarded; failures must not block the session.
- **Idempotent** — safe to run on every session start; repeated runs are no-ops when already healthy.
- **Concurrent** — multiple harness sessions may start at once; hooks must not assume exclusive ownership of the machine.
- **Fault-tolerant** — wrapped so a bad heal or busy port cannot take down session start (`|| true` / equivalent).

Hooks are short-budget work. Session-start hook commands carry an explicit timeout (hundreds of seconds, not “as long as ETL needs”). Anything that can run for minutes does not belong on session start.

### Session start

On session start, Stockroom does two things through the shim:

1. **`shim rectify`** — heal the on-path shim and ensure the engine environment (see [Heal](packaging.md#heal) and [The stockroom shim](packaging.md#the-stockroom-shim)).
2. **`stockroom dashboard`** — launch (or re-print) the local dashboard URL.

Session start does **not** ingest, embed, or migrate as its primary work. Those are heavier, longer, and already owned by the schedule and explicit CLI/skill paths. Putting them on the hook would fight timeout limits and turn every new chat into an inelegant ETL termination race.

### Cursor beforeSubmitPrompt suspenders

On Cursor, `sessionStart` has been observed to miss on some macOS setups. Cursor also registers a trimmed **`beforeSubmitPrompt`** hook that must never block prompt send: it emits `{"continue":true}` immediately, then backgrounds a **path-only** `shim rectify --path-only` (create/rebake the on-path shim; **skip** `ensure-env`). Full ensure + dashboard launch stay on `sessionStart` only. Claude Code does not get this suspenders event.

## Scheduled ingest and embed

Freshness is a nightly `stockroom ingest && stockroom embed` (incremental) on the platform scheduler — cron on Linux/WSL, launchd on macOS. The job invokes the shim by name; it does not embed a raw engine path. Output lands under stockroom home logs.

`sr-initialize` offers to install the job once. Manual catch-up remains available via CLI when results feel stale — see [User Guide → Load the Warehouse](../user-guide/load/index.md).

Backfill of *legacy* stores is deliberately not on this schedule, or any other — see [Backfill](backfill.md).

## Dashboard launch

The dashboard is a **local, read-only, fully offline** metrics UI (default port 58008). Front-end assets are vendored — no CDN or external web requests at runtime. It does not ingest, embed, or migrate; warehouse content freshness is owned by ingest/embed/backfill. The long-lived listener caches API JSON until the warehouse file's on-disk fingerprint changes, so a refresh does not re-query when nothing has been written.

Session-start hooks attempt to launch it automatically. The CLI is idempotent: if something already listens on the port, the command still prints the URL and exits cleanly. The process uses a torch-safe engine env (same shim contract as other subcommands) and opens the warehouse through `open_current()` so a UI process never becomes the migrator — see [Warehouse](warehouse.md#concurrency-and-open-paths).

When the listener cannot serve real static UI (missing `index.html`, unknown document path, stale assets after a plugin move), it returns an in-memory **recovery HTML** page: short harness-first rundown (new chat / prompt → `sr-initialize` if the shim stays dead) plus a link to the user-guide troubleshooting section — not bare JSON `{"error":"not found"}`, and not circular `stockroom …` CLI while PATH is broken. API and session-miss responses stay JSON.

## Rendered-out artifacts

Shim, harness hooks (`hooks/*.json`), and scheduler entries are each owned by one module with structural idempotency. No rendered artifact carries a raw engine path — callers invoke `stockroom` by name so plugin moves are healed by rectify rather than by rewriting every consumer.

Harness hooks are not the same JSON shape or event: Cursor uses flat `sessionStart` / `beforeSubmitPrompt` commands; Claude Code uses nested `SessionStart` / `hooks[]` / `type: "command"`. Do not copy one harness's structure into the other.

## Related procedures

- Operating the dashboard: [User Guide → Dashboard](../user-guide/dashboard.md)
- Ingest, embed, and scheduling how-to: [User Guide → Load the Warehouse](../user-guide/load/index.md)
- Contributor schedule / hook iteration: [Contributing → Iteration](../contributing/iteration/index.md)
