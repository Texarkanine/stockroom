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

Contributor localdev wires a Cursor skills mirror after you uninstall the marketplace plugin — see [Preparation](../../contributing/preparation.md). Confirm `make localdev-status` shows the skills mirror, reload the window, and use `HARNESS=cursor make localdev` (Claude uses `claude --plugin-dir` instead of a skills mirror). Marketplace sessionStart hooks are gone after uninstall; the dashboard remains reachable via `stockroom dashboard` / `make local-dashboard`.

## Installed layout

### `stockroom: command not found`

Prefer, in order:

1. **`sr-initialize`** when you can spend an agent turn — it re-probes and only does what is still missing ([Quickstart](../quickstart.md)).
2. **New harness session** — session-start hooks run `shim rectify`, which can create a missing on-path shim or rebake an owned one after a plugin path move.
3. **Last resort: bind the shim yourself** — when the marketplace plugin is already installed and you cannot spend an agent turn.

What lands on disk: [Installed layout](../installed-layout.md).

#### Last resort: bind the shim yourself

The shim is **baked** to one engine directory (`…/skills/sr-search`). Bind the install that is already on disk — not a random git clone. The same recipe lives in your installed plugin under `skills/sr-initialize/SKILL.md`, btw.

1. Find the engine dir (pick the marketplace/plugin tree you actually run — not a contributor checkout unless that is intentional):

	```bash
	find ~/.cursor/plugins ~/.claude/plugins -type d -path '*/skills/sr-search' 2>/dev/null
	```

	If a broken on-path shim still exists, its header names the baked directory: `grep '^# STOCKROOM_APP_DIR=' "$(command -v stockroom)"`.

2. Set `APP_DIR` to that absolute path and choose the owner for this harness (`cursor` or `claude`):

	```bash
	APP_DIR=/absolute/path/to/skills/sr-search
	OWNER=cursor   # or: claude

	PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config \
	python -m stockroom shim install --owner "$OWNER"
	```

3. Confirm:

	```bash
	command -v stockroom
	stockroom --version
	```

If the installer warns that `~/.local/bin` is not on `PATH`, add it and retry the check.

**Ownership:** if install refuses because another owner's shim is alive, read the refusal line. Replacing a live foreign shim needs explicit `--takeover` — prefer `sr-initialize` or consent carefully.

### Shim refuses with a one-line remedy

Follow the remedy printed on stderr. Often that is: open a new session so `shim rectify` can heal, or re-run `sr-initialize`. If you cannot use an agent turn and the remedy is effectively “rebind the launcher,” use the [last-resort bind](#last-resort-bind-the-shim-yourself) under `stockroom: command not found`.

### Engine env cannot import locked deps

Let session-start heal run (`shim rectify` includes ensure-env), run `stockroom shim ensure-env` yourself, or re-run `sr-initialize`.

## Ingest

### Empty or sparse results after first install

Confirm the first ingest + embed finished (`sr-initialize`). Wait for the nightly schedule, or run ingest/embed yourself — [Load the Warehouse](../load/index.md) · [CLI](../../advanced/cli.md).

### Weak semantic results for recent work

Silent staleness is possible: ingest may have new messages that are not embedded yet. Catch up with `stockroom ingest` then `stockroom embed` before concluding the content is absent — [Load the Warehouse](../load/index.md).

### Nightly schedule installed but nothing updates

Check `stockroom schedule status`. If the cron daemon is not running, the entry is written but will not fire (WSL: `sudo service cron start`, or enable systemd). See [Scheduling](../load/schedule.md).

## Search

### SQL errors on write-looking statements

Read surfaces open the warehouse read-only by construction — use ingest/embed for writes ([Search](../search.md) · [CLI](../../advanced/cli.md)).

### Truncated-looking cells in output

Truncation is read-time only; use a higher `--detail` (or refetch a targeted row). Full content remains in the warehouse ([CLI](../../advanced/cli.md)).

### Semantic search returns nothing useful

Confirm the warehouse has embeddings (ingest + embed), then decide structured vs meaning-based — [Search](../search.md). If the error cites torch / the environment, see [Torch](torch.md).

## Dashboard

### Dashboard UI will not load

Something is answering on the dashboard port, but you are not getting the real UI — blank page, odd HTML, or the short in-browser recovery page that says the dashboard could not load this page. There is no single root cause; the steps below are common things worth trying, not a diagnosis of your machine.

#### Things that sometimes contribute

- A **stale dashboard process** left over after a plugin update, still bound to the port but no longer able to serve current static assets.
- An on-path **`stockroom` shim** that is missing, or still baked to an old plugin path. Harness hooks are one way that path gets refreshed (they can see `CURSOR_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT`). If `stockroom` itself is missing or refuses, terminal commands that start with `stockroom …` may not be able to find the correct install on their own.
- Less often for *this* symptom: a broken **engine env** (locked deps missing from the engine `.venv`) that blocks starting a *new* listener. The dashboard does not use Torch, so Torch issues are usually a different problem — [Torch](torch.md) · [Engine env cannot import locked deps](#engine-env-cannot-import-locked-deps).

#### Things to try

1. **From the harness.** Open a **new chat** and run **`/sr-dashboard`** (Claude Code: `/stockroom:sr-dashboard`), or submit a short prompt so session-start / Cursor’s before-submit suspenders get a chance to run. Reload [http://127.0.0.1:58008/](http://127.0.0.1:58008/) afterward.
2. **Cursor hooks.** If auto-heal never seems to run, check the third-party plugins setting — [Quickstart](#cursor-hooks--auto-dashboard-never-fire).
3. **If `stockroom` is missing or refuses.** In a chat, try **`/sr-initialize`** (Claude Code: `/stockroom:sr-initialize`) and ask it to restore the on-path shim and get the dashboard serving. That skill can see the plugin tree even when the shim cannot.
4. **If `stockroom --version` already works** but the page is still wrong, `stockroom dashboard --replace` can replace a stale listener. If the shim is not healthy yet, `--replace` often does nothing useful.
5. **Without an agent turn.** Last-resort manual bind — [last-resort bind](#last-resort-bind-the-shim-yourself) under [`stockroom: command not found`](#stockroom-command-not-found).

The in-browser recovery page links here for the longer walkthrough. API clients still see JSON 404 for unknown `/api/*` routes.

### Port 58008 already in use

When `stockroom --version` works but the UI looks stale, try `stockroom dashboard --replace` (or stop the old `stockroom.dashboard` process once, then `/sr-dashboard`) — [Dashboard](../dashboard.md). If you are not sure the shim is healthy, the broader checklist above may be a better starting point.

### Auto-start missing on Cursor

Third-party plugins setting ([Quickstart](#cursor-hooks--auto-dashboard-never-fire) above). If that is already on and nothing seems to auto-heal, the [Dashboard UI will not load](#dashboard-ui-will-not-load) checklist is the next place to look.

## Still stuck

- Ask the agent with `/sr-search` (or Claude `/stockroom:sr-search`) and describe the error text — [Skill index](../skills.md).
- Torch / embeddings / heal soft-fails: [Torch](torch.md).
- Contributors debugging from a checkout: [Preparation](../../contributing/preparation.md) · [Iteration](../../contributing/iteration/index.md).
