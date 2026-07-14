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
3. **Last resort: bind the shim yourself** — when the marketplace plugin is already installed and you cannot spend an agent turn ([recipe below](#last-resort-bind-the-shim-yourself)).

What lands on disk: [Installed layout](../installed-layout.md).

#### Last resort: bind the shim yourself

The shim is **baked** to one engine directory (`…/skills/sr-search`). Bind the install that is already on disk — not a random git clone. The same recipe lives in your installed plugin under `skills/sr-initialize/SKILL.md` (Step 7: Bind the `stockroom` command).

1. Find the engine dir (pick the marketplace/plugin tree you actually run — not a contributor checkout unless that is intentional):

```bash
find ~/.cursor/plugins ~/.claude/plugins -type d -path '*/skills/sr-search' 2>/dev/null
```

If a broken on-path shim still exists, its header names the bake: `grep '^# STOCKROOM_APP_DIR=' "$(command -v stockroom)"`.

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

**Ownership:** if install refuses because another owner’s shim is alive, read the refusal line. Replacing a live foreign shim needs explicit `--takeover` (and usually a reason you are sure) — prefer `sr-initialize` or consent carefully. Contributor checkouts use `make shim` (owner `dev`) from [Preparation](../../contributing/preparation.md), not this recipe.

Torch / env heal beyond binding the launcher: [Torch](torch.md) · `sr-initialize`.

### Shim refuses with a one-line remedy

Follow the remedy printed on stderr. Often that is: open a new session so `shim rectify` can heal, or re-run `sr-initialize`. If you cannot use an agent turn and the remedy is effectively “rebind the launcher,” use the [last-resort bind](#last-resort-bind-the-shim-yourself) under `stockroom: command not found`.

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
- Contributors debugging from a checkout: [Preparation](../../contributing/preparation.md) · [Iteration](../../contributing/iteration.md).
