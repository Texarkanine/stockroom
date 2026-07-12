# Dashboard

The stockroom dashboard is a **local, read-only, fully offline** metrics UI over your warehouse — an at-a-glance view of cross-harness agentic-coding history. It does not ingest, embed, or migrate; freshness is owned by [Load the Warehouse](ingest.md).

Default URL: [http://localhost:58008](http://localhost:58008/) (also `http://127.0.0.1:58008/`). Every front-end asset is vendored — no CDN at runtime.

![Stockroom dashboard — aggregate metrics](../img/stockroom-dashboard-top-light.png)

## `sr-dashboard`

The skill launches (or re-prints) the dashboard URL. Use it when you want the UI, not a SQL or semantic answer.

| Harness | Slash form |
| --- | --- |
| Cursor | `/sr-dashboard` |
| Claude Code | `/stockroom:sr-dashboard` |

```bash
stockroom dashboard
```

Stdout is a single URL line — relay that to the user. The server is idempotent: if something is already listening on the port, the command still prints the URL and exits cleanly.

Session-start hooks also launch the dashboard automatically when plugin hooks are registered (Cursor: third-party plugins setting on [Quickstart](quickstart.md)). Prefer `/sr-dashboard` or `stockroom dashboard` if auto-start never fires.

## What you see

### Metrics

Harness filters, time ranges, and Aggregate / Compare views over sessions, messages, projects, daily activity, tool distribution, and related rollups. The warehouse is machine-scoped: the UI stays up across harness sessions and is not stopped when one IDE closes.

### Session inspection

Open a conversation from Recent Sessions (or a deep link) to read the thread, copy a deep-link, or export markdown/JSON when in-dashboard rendering is not enough.

![Stockroom dashboard — session conversation view](../img/stockroom-dashboard-convo-light.png)

Deep-link shape (both query params required):

```text
http://127.0.0.1:58008/?view=session&harness={harness}&session={session_id}
```

## Lifecycle notes

- After a plugin update moves the engine path, the next session start should replace a stale owned listener with one from the healed engine.
- A dashboard started before that identity tracking existed may need one manual stop (`kill` the old `stockroom.dashboard` process) before automatic replace can take over.
- Port conflicts and auto-start misses: [Troubleshooting · Dashboard](troubleshooting/index.md#dashboard).

For search (not browsing), see [Search](search.md). For every skill at a glance, see [Skill index](skills.md).
