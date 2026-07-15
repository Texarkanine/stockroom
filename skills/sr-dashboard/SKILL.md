---
name: sr-dashboard
description: Open the local stockroom dashboard — a read-only, fully offline at-a-glance view of cross-harness agentic-coding history. Reach for this when you (or the user) want the metrics UI URL, not SQL or semantic search.
enable-model-invocation: true
---

# sr-dashboard

`sr-dashboard` launches the **local read-only dashboard** over the stockroom warehouse and prints its URL. The server is idempotent: if something is already listening on the dashboard port, the command still prints the URL and exits cleanly. Every front-end asset is vendored — no CDN, no network fetch at runtime.

## When to use sr-dashboard

Reach for `sr-dashboard` when the need is **the UI**, not a query:

- The user asks to open, show, or launch the stockroom dashboard.
- You need the local URL to hand back (`http://127.0.0.1:58008/` by default).
- A session-start path already launched it and you only need to confirm or re-print the URL.

**Do not** use `sr-dashboard` for exact SQL lookups (`sr-query`) or meaning-based recall (`sr-semantic`). When you are not sure which surface fits, that judgement belongs to the **`sr-search`** skill.

## How to invoke the engine

```bash
stockroom dashboard
```

Stdout is a single URL line (for example `http://127.0.0.1:58008/`). Relay that URL to the user; do not invent a different host or port.

If `command -v stockroom` fails, the machine isn't set up yet: tell the user to run the **`sr-initialize`** skill, and don't attempt any other invocation.

## Deep-links

### Sessions list

Browse a filtered, paginated sessions list (independent of the metrics pane filters):

```text
{dashboard_base}/?view=sessions&harness={harness}&per_page=50
```

Optional query params: repeated `harness`, `since` / `until` (ISO-8601; omit both for **All** / unwindowed), `page` (omit when 1), `per_page` (`25` | `50` | `100` | `all`; default `50`). Example: `http://127.0.0.1:58008/?view=sessions&harness=cursor&per_page=25&page=2`

### Session reconstruction

When you already know a `(harness, session_id)` pair and want to open that conversation (or offer a link the operator can paste):

```text
{dashboard_base}/?view=session&harness={harness}&session={session_id}
```

Example: `http://127.0.0.1:58008/?view=session&harness=cursor&session=abc123`

Both `harness` and `session` are required. URL-encode opaque session ids. Sessions panel and list rows use the same template; the session pane has **Copy deep-link**. Use the browser Back button to leave the list or session views — there is no custom back control. Export markdown/JSON from the session pane when basic in-dashboard rendering is not enough.

## Guardrails

- **Thin launch only.** Run `stockroom dashboard` as shown. Do not pass `--foreground` from this skill — that flag is for the detached child / debugging, not the agent path.
- **Do not ingest or migrate** from this skill. The dashboard opens read-only; schema and data freshness are owned by `sr-initialize` and the nightly schedule.
- **Missing command → initialize.** Never invent an alternate engine invocation; the next action is always `sr-initialize`.

## System model

For warehouse layout, harness coverage, and how stockroom fits together, see [`../sr-search/references/system-model.md`](../sr-search/references/system-model.md).
