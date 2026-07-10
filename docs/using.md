# Using Stockroom

## Install

The committed repo is the install layout — dual manifests over a shared `skills/` tree, no build or bundle step.

### Marketplace

**Cursor** ([marketplace docs](https://cursor.com/docs/plugins)):

1. Open **Cursor Settings → Plugins**.
2. Paste `https://github.com/Texarkanine/txrk9-agent-plugins` into the search/paste-link box.
3. Install the `stockroom` plugin from that marketplace.
4. Run first-time setup (`/sr-initialize`).

**Claude Code** ([discover plugins](https://code.claude.com/docs/en/discover-plugins)):

1. Run `/plugin` → **Marketplaces**, or `claude plugin marketplace add Texarkanine/txrk9-agent-plugins`.
2. Install with `/plugin install stockroom@txrk9-agent-plugins` (exact marketplace id may match the catalog `name` field).
3. Run first-time setup (`/stockroom:sr-initialize`).

Cursor’s “add plugins from folder” UI expects a **marketplace** manifest (`.cursor-plugin/marketplace.json`). Pointing it at this repo fails on purpose — stockroom is a plugin, not a marketplace. The catalog lives in `txrk9-agent-plugins`.

### Local / development load

Use these while iterating. They are not the supported end-user path.

**Cursor** ([test plugins locally](https://cursor.com/docs/plugins)):

```bash
mkdir -p ~/.cursor/plugins/local
# Prefer a real copy; symlinks to a repo outside this tree are often rejected.
rsync -a --delete \
  --exclude .git --exclude .venv --exclude '**/__pycache__' \
  /path/to/stockroom/ ~/.cursor/plugins/local/stockroom/
```

Reload the window (**Developer: Reload Window**). `.cursor-plugin/plugin.json` must sit at `~/.cursor/plugins/local/stockroom/.cursor-plugin/plugin.json`.

**Claude Code** ([create plugins](https://code.claude.com/docs/en/plugins)):

```bash
# Session-scoped load from a checkout (no marketplace, no install cache):
claude --plugin-dir /path/to/stockroom
```

For a longer-lived Claude install you still go through a marketplace (local or remote) that lists the plugin.

## First-time setup

After the plugin is loaded, run **`sr-initialize`** once (Cursor: `/sr-initialize`; Claude: `/stockroom:sr-initialize`). It checks prerequisites, provisions the per-machine torch wheel, binds the on-path `stockroom` command, offers nightly ingest+embed scheduling, and runs the first full ingest + embed. Re-runs are safe: it re-probes and only does what is still missing.

## Skills and invocation

Invocation forms differ by harness. Engine calls after setup are always `stockroom <subcommand>` on PATH; only the skill slash forms below are harness-specific.

| Skill | Cursor | Claude Code | Role |
| --- | --- | --- | --- |
| `sr-initialize` | `/sr-initialize` | `/stockroom:sr-initialize` | Machine setup (torch, shim, schedule, first ingest) |
| `sr-search` | `/sr-search` | `/stockroom:sr-search` | Friendly default search (routes to query / semantic) |
| `sr-query` | `/sr-query` | `/stockroom:sr-query` | Read-only SQL against the warehouse |
| `sr-semantic` | `/sr-semantic` | `/stockroom:sr-semantic` | Meaning-based (vector) search |
| `sr-dashboard` | `/sr-dashboard` | `/stockroom:sr-dashboard` | Open the local metrics dashboard |

## Usage after setup

- Prefer **`/sr-search`** (Cursor) or **`/stockroom:sr-search`** (Claude Code) when you are unsure whether the question is structured or meaning-based.
- Use **`/sr-query`** / **`/stockroom:sr-query`** for exact SQL, filters, and counts.
- Use **`/sr-semantic`** / **`/stockroom:sr-semantic`** for recall by meaning.
- Use **`/sr-dashboard`** / **`/stockroom:sr-dashboard`** for the at-a-glance UI (also launched by the session-start hook where the harness PATH is complete).

On some Cursor/WSL hosts the session-start hook’s PATH omits `~/.local/bin`, so auto-dashboard may not start — see [#12](https://github.com/Texarkanine/stockroom/issues/12). Use `/sr-dashboard` or `stockroom dashboard` instead.
