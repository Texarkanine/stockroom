# Install

The committed repo is the install layout — dual manifests over a shared `skills/` tree, no build or bundle step for the plugin payload.

End-user setup is **marketplace install → `sr-initialize`**. Do not treat `make` / `uv` from a git clone as an alternate onboarding path; those are for contributors (see the [contributor guide](../contributor-guide/development.md)).

## Marketplace

### Cursor

Cursor [marketplace docs](https://cursor.com/docs/plugins):

1. Open **Cursor Settings → Plugins**.
2. Paste `https://github.com/Texarkanine/txrk9-agent-plugins` into the search/paste-link box.
3. Install the `stockroom` plugin from that marketplace.
4. Enable **Include third-party Plugins, Skills, and other configs** (Cursor Settings). Plugin hooks do not register without this until [Cursor’s plugin-hooks bug](https://forum.cursor.com/t/plugin-hooks-not-loading-into-cursor-ide/156702) is fixed:

   ![Include third-party Plugins, Skills, and other configs — toggle on](../img/3rd-party-configs.png)

5. Run first-time setup (`/sr-initialize`).

### Claude Code

Claude Code [discover plugins](https://code.claude.com/docs/en/discover-plugins):

1. Run `/plugin` → **Marketplaces**, or `claude plugin marketplace add Texarkanine/txrk9-agent-plugins`.
2. Install with `/plugin install stockroom@txrk9-agent-plugins` (exact marketplace id may match the catalog `name` field).
3. Run first-time setup (`/stockroom:sr-initialize`).

Cursor’s “add plugins from folder” UI expects a **marketplace** manifest (`.cursor-plugin/marketplace.json`). Pointing it at this repo fails on purpose — stockroom is a plugin, not a marketplace. The catalog lives in `txrk9-agent-plugins`.

## First-time setup

After the plugin is loaded, run **`sr-initialize`** once (Cursor: `/sr-initialize`; Claude: `/stockroom:sr-initialize`). It checks prerequisites, provisions the per-machine torch wheel, binds the on-path `stockroom` command, offers nightly ingest+embed scheduling, and runs the first full ingest + embed. Re-runs are safe: it re-probes and only does what is still missing.

## Local / development load

Use these while iterating on the plugin itself. They are not the supported end-user path.

### Cursor

Cursor [test plugins locally](https://cursor.com/docs/plugins):

```bash
mkdir -p ~/.cursor/plugins/local
# Prefer a real copy; symlinks to a repo outside this tree are often rejected.
rsync -a --delete \
  --exclude .git --exclude .venv --exclude '**/__pycache__' \
  /path/to/stockroom/ ~/.cursor/plugins/local/stockroom/
```

Reload the window (**Developer: Reload Window**). `.cursor-plugin/plugin.json` must sit at `~/.cursor/plugins/local/stockroom/.cursor-plugin/plugin.json`. Excluding `.venv` is intentional — the next `sessionStart` hook runs `shim rectify`, which ensures locked deps and reinstalls torch from the hashed freeze under stockroom home (written by `sr-initialize` / contributor `make torch`). If you never froze a stack, run `sr-initialize` once (or see the [torch contributor docs](../contributor-guide/torch.md)).

### Claude Code

Claude Code [create plugins](https://code.claude.com/docs/en/plugins):

```bash
# Session-scoped load from a checkout (no marketplace, no install cache):
claude --plugin-dir /path/to/stockroom
```

For a longer-lived Claude install you still go through a marketplace (local or remote) that lists the plugin.
