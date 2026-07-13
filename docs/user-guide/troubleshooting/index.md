# Troubleshooting

Human-oriented recovery for common failure modes. Agents already carry short recovery tables in each `SKILL.md`; this page is the longer catalog with UI and environment checks.

When in doubt: re-run **`sr-initialize`**. It re-probes and only does what is still missing.

Sections follow the [user guide](../index.md) order. Each symptom is its own heading so you can deep-link it.

## Quickstart

### Skills missing after marketplace install

Reload the window; confirm the plugin is enabled in the harness plugin UI.

### Cursor hooks / auto-dashboard never fire

Enable **Include third-party Plugins, Skills, and other configs** (see the [Quickstart](../quickstart.md) screenshot). Then reload.

### “Add plugins from folder” rejects this repo

Expected — stockroom is a **plugin**, not a marketplace. Install via [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins).

### Local checkout skills do not load

Contributor localdev wires a Cursor skills mirror after you uninstall the marketplace plugin — see [Local workflow](../../contributing/local-workflow.md). Confirm `make localdev-status` shows the skills mirror, reload the window, and use `HARNESS=cursor make localdev` (Claude uses `claude --plugin-dir` instead of a skills mirror). Marketplace sessionStart hooks are gone after uninstall; the dashboard remains reachable via `stockroom dashboard` / `make local-dashboard`.

## Installed layout

### `stockroom: command not found`

The machine is not initialized — run `sr-initialize` ([Quickstart](../quickstart.md)). What lands on disk: [Installed layout](../installed-layout.md).

### Shim refuses with a one-line remedy

Follow the remedy. Usually: re-run `sr-initialize`, or open a new session so `shim rectify` can heal after a plugin path move.

### Engine env cannot import locked deps

Let session-start heal run, or re-run `sr-initialize`.

## Ingest

### Empty or sparse results after first install

Confirm the first ingest + embed finished (`sr-initialize`). Wait for the nightly schedule, or run ingest/embed yourself — [Load the Warehouse](../ingest.md) · [CLI](../../advanced/cli.md).

### Weak semantic results for recent work

Silent staleness is possible: ingest may have new messages that are not embedded yet. Catch up with `stockroom ingest` then `stockroom embed` before concluding the content is absent — [Load the Warehouse](../ingest.md).

### Nightly schedule installed but nothing updates

Check `stockroom schedule status`. If the cron daemon is not running, the entry is written but will not fire (WSL: `sudo service cron start`, or enable systemd). See [Scheduling](../ingest.md#scheduling).

## Search

### SQL errors on write-looking statements

Read surfaces open the warehouse read-only by construction — use ingest/embed for writes ([Search](../search.md) · [CLI](../../advanced/cli.md)).

### Truncated-looking cells in output

Truncation is read-time only; use a higher `--detail` (or refetch a targeted row). Full content remains in the warehouse ([CLI](../../advanced/cli.md)).

### Semantic search returns nothing useful

Confirm the warehouse has embeddings (ingest + embed), then decide structured vs meaning-based — [Search](../search.md). If the error cites torch / the environment, see [Torch](torch.md).

## Dashboard

### Port 58008 already in use / stale UI after plugin update

Session start should replace an owned listener. If a pre-identity-tracking process remains, stop the old `stockroom.dashboard` process once, then `/sr-dashboard` — [Dashboard](../dashboard.md).

### Auto-start missing on Cursor

Third-party plugins setting ([Quickstart](#cursor-hooks--auto-dashboard-never-fire) above); then `/sr-dashboard` or `stockroom dashboard` — [Dashboard](../dashboard.md).

## Still stuck

- Ask the agent with `/sr-search` (or Claude `/stockroom:sr-search`) and describe the error text — [Skill index](../skills.md).
- Torch / embeddings / heal soft-fails: [Torch](torch.md).
- Contributors debugging from a checkout: [Local workflow](../../contributing/local-workflow.md) · [Development](../../contributing/development.md).
