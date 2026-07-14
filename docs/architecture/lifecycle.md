# Lifecycle

When Stockroom work runs on a live machine: hooks, the nightly schedule, and the dashboard process. This is *when* things fire — not how to install or how to write SQL.

## Hook doctrine

Harness session-start hooks are designed to be:

- **Fire-and-forget** — stdout/stderr discarded; failures must not block the session.
- **Idempotent** — safe to run on every session start; repeated runs are no-ops when already healthy.
- **Concurrent** — multiple harness sessions may start at once; hooks must not assume exclusive ownership of the machine.
- **Fault-tolerant** — wrapped so a bad heal or busy port cannot take down session start (`|| true` / equivalent).

Hooks are short-budget work. Cursor’s hook command carries an explicit timeout (hundreds of seconds, not “as long as ETL needs”). Anything that can run for minutes does not belong on session start.

## Session start

On session start, Stockroom does two things through the shim:

1. **`shim rectify`** — heal the on-path shim and ensure the engine environment (see [Packaging](packaging.md)).
2. **`stockroom dashboard`** — launch (or re-print) the local dashboard URL.

Session start does **not** ingest, embed, or migrate as its primary work. Those are heavier, longer, and already owned by the schedule and explicit CLI/skill paths. Putting them on the hook would fight timeout limits and turn every new chat into an inelegant ETL termination race.

## Scheduled ingest and embed

Freshness is a nightly `stockroom ingest && stockroom embed` (incremental) on the platform scheduler — cron on Linux/WSL, launchd on macOS. The job invokes the shim by name; it does not embed a raw engine path. Output lands under stockroom home logs.

`sr-initialize` offers to install the job once. Manual catch-up remains available via CLI when results feel stale — see [User Guide → Load the Warehouse](../user-guide/ingest.md).

## Dashboard launch

The dashboard is a **local, read-only, fully offline** metrics UI (default port 58008). Front-end assets are vendored — no CDN or external web requests at runtime. It does not ingest, embed, or migrate; freshness is owned by ingest/embed.

Session-start hooks attempt to launch it automatically. The CLI is idempotent: if something already listens on the port, the command still prints the URL and exits cleanly. The process uses a torch-safe engine env (same shim contract as other subcommands) and opens the warehouse through `open_current()` so a UI process never becomes the migrator — see [Warehouse](warehouse.md).

## Rendered-out artifacts

Shim, harness hooks (`hooks/*.json`), and scheduler entries are each owned by one module with structural idempotency. No rendered artifact carries a raw engine path — callers invoke `stockroom` by name so plugin moves are healed by rectify rather than by rewriting every consumer.

## Related procedures

- Operating the dashboard: [User Guide → Dashboard](../user-guide/dashboard.md)
- Ingest, embed, and scheduling how-to: [User Guide → Load the Warehouse](../user-guide/ingest.md)
- Contributor schedule / hook iteration: [Contributing → Iteration](../contributing/iteration.md)
