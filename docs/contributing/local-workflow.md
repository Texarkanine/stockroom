# Local Workflow

## Exit Normal Install

To get out of a normal Stockroom install in preparation for local development...

### 1. Make a Backup

```bash
cp -r ~/.local/share/stockroom/warehouse.db ~/warehouse.db.backup
```

### 2. Uninstall the Plugin

Un-install the Stockroom plugin from your harness(es). Close the harnesses.

### 3. Stop the Dashboard

```bash
stockroom dashboard stop
```

## Prepare Local Checkout

Once you do not have an active Stockroom engine hooked into a harness, nor pointed at by the Stockroom CLI shim, you're ready to hook up a local checkout.

### 1. Shim Takeover

```bash
make shim TAKEOVER=1 FORCE=1
```

Now, the `stockroom` CLI points at the engine in your local checkout. Python code changes you make *will* be reflected.

### 2. Harness Wiring

TODO: We need the harness to find the skills from the local checkout AND THE HOOKS.

Skills is easy, `make localdev` does skills (TODO: make one for Cursor).

Hooks is harder. Maybe we have localdev ALSO put hooks into the CURRENT PROJECT, also gitignored? But those only fire in THIS project... BUT ALSO the hook uses the existing shim, so once the shim is taken over, the hook would work. But we can't JUST install the hook w/out the skills...

### 3. Dependency Sync

```bash
stockroom shim ensure-env
```

This will re-create the python virtual environment in the new location, including re-installing the correct version of PyTorch.

### 4. Done!

Now, you have

1. `stockroom` CLI pointing at your local checkout's python code
2. When working in the Stockroom project,
    - your `/sr-*` skills go to the local checkout copies
    - your sessionStart hook fires to start the dashboard

You are now ready to start developing!

---

OLD CONTENTS BELOW: 

This page is the contributor round-trip: leave a normal install, hack exclusively from a checkout, verify, and return to the released/plugin install without a hybrid half-state.

End users stay on [`sr-initialize`](../user-guide/quickstart.md) / the marketplace. The Makefile is the **checkout** entrypoint — not an alternate bootstrap for operators who only want Stockroom installed.

Day-to-day targets, the torch-safe `uv` contract, and ad-hoc engine invocation - and everything else you need once you've switched to a local checkout - live in [Development](development.md).

## Surfaces

Depending on what you want to hack on, 

| Surface | What it is | When to use it |
| --- | --- | --- |
| `make localdev` | Symlink farm under `.cursor/skills/stockroom-local/` plus a managed pre-commit guard | Optional: iterate on **skills** from the checkout without a full plugin copy |
| `make plugin-local` | `rsync` of this repo into `~/.cursor/plugins/local/stockroom/` (overridable `PLUGIN_LOCAL_DEST`) | Cursor: load hooks/skills/plugin.json as an installed **local plugin** |
| `claude --plugin-dir /path/to/stockroom` | Session-scoped Claude Code plugin load | Claude: try the checkout without a marketplace install |
| On-path shim (`make shim`) | Baked `stockroom` on `PATH` with owner `dev` | Every enter path that needs ad-hoc CLI from this checkout |

## Enter

Recommended order (named atoms + human gates):

```bash
make sync          # lock-faithful engine env (strips torch)
make torch         # reinstall torch out-of-band + freeze under stockroom home
make shim          # bake this checkout onto PATH (owner: dev)
# If shim install refuses because a dead foreign bake still owns PATH:
make shim TAKEOVER=1
```

Then load the plugin surface you need:

**Cursor (full plugin):**

```bash
make plugin-local
# Reload the window: Developer → Reload Window
```

Confirm `.cursor-plugin/plugin.json` sits at `~/.cursor/plugins/local/stockroom/.cursor-plugin/plugin.json` (or under your `PLUGIN_LOCAL_DEST`). Enable **Include third-party Plugins, Skills, and other configs** if hooks do not fire — see [Troubleshooting](../user-guide/troubleshooting/index.md#cursor-hooks--auto-dashboard-never-fire).

**Claude Code (session-scoped):**

```bash
claude --plugin-dir /path/to/stockroom
```

For a longer-lived Claude install you still go through a marketplace that lists the plugin.

**Optional skills-only mirror** (in addition to, or instead of, a full plugin copy when you only care about skill bodies):

```bash
make localdev
```

### Enter footguns

- **`make sync` / `make ci` strips torch.** Re-run `make torch` before embed/semantic work. Operator contract: [Torch](../user-guide/troubleshooting/torch.md).
- **Shim is succeed-or-refuse.** It never guesses an engine location. Use `TAKEOVER=1` only for a **dead foreign** bake that still owns `~/.local/bin/stockroom` — not as a casual default.
- **Session-start rectify on a `plugin-local` copy** can re-heal the shim toward that copy’s baked path. If you need owner `dev` pointing at the checkout, re-run `make shim` (or `TAKEOVER=1` when appropriate) after reload and confirm with `stockroom doctor`.
- **Do not symlink** the checkout into `~/.cursor/plugins/local/stockroom/` — use `make plugin-local`.

## Verify

```bash
make localdev-status   # skills-mirror / plugin-local / pre-commit hints (read-only)
stockroom doctor       # bake, owner, env health
make ci                # engine gate (re-run make torch afterward if you need embeddings)
make docs-build        # when docs change
make reuse             # when licensing-relevant paths change
```

Confirm the harness is loading **your** checkout (local plugin path or `--plugin-dir`), not only the marketplace install.

## Exit

Undo mechanical localdev state, then restore a normal install:

```bash
make localdev-clean    # remove stockroom-local symlinks + managed pre-commit block (idempotent)
rm -rf ~/.cursor/plugins/local/stockroom   # or your PLUGIN_LOCAL_DEST
```

Then get a normal on-path shim again:

- Reinstall / enable the marketplace plugin and let session-start `shim rectify` rebake, **or**
- Re-run [`sr-initialize`](../user-guide/quickstart.md) (re-probes; only does what is still missing).

Exit cannot fully automate marketplace UI reinstall or IDE reload — those stay human steps. Goal: no leftover skills-mirror, no stray `plugins/local` copy you still treat as “the” install, and a shim owned by the released/plugin path rather than a half-dead `dev` bake.

Check leftovers:

```bash
make localdev-status
stockroom doctor
```
