# Local workflow

This page is the contributor round-trip: leave a normal install, hack exclusively from a checkout, verify, and return to the released/plugin install without a hybrid half-state.

End users stay on [`sr-initialize`](../user-guide/quickstart.md) / the marketplace. The Makefile is the **checkout** entrypoint — not an alternate bootstrap for operators who only want Stockroom installed.

Day-to-day targets, the torch-safe `uv` contract, and ad-hoc engine invocation live in [Development](development.md).

## Surfaces (do not conflate)

| Surface | What it is | When to use it |
| --- | --- | --- |
| `make localdev` | Symlink farm under `.cursor/skills/stockroom-local/` plus a managed pre-commit guard | Optional: iterate on **skills** from the checkout without a full plugin copy |
| `make plugin-local` | `rsync` of this repo into `~/.cursor/plugins/local/stockroom/` (overridable `PLUGIN_LOCAL_DEST`) | Cursor: load hooks/skills/plugin.json as an installed **local plugin** |
| `claude --plugin-dir /path/to/stockroom` | Session-scoped Claude Code plugin load | Claude: try the checkout without a marketplace install |
| On-path shim (`make shim`) | Baked `stockroom` on `PATH` with owner `dev` | Every enter path that needs ad-hoc CLI from this checkout |

`make localdev` and `make plugin-local` solve different problems. Skills-mirror is not a substitute for a Cursor local plugin copy. Cursor prefers a **real copy** under `plugins/local` — do not symlink the repo into that tree.

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
- Re-run [`sr-initialize`](../user-guide/troubleshooting/index.md) (re-probes; only does what is still missing).

Exit cannot fully automate marketplace UI reinstall or IDE reload — those stay human steps. Goal: no leftover skills-mirror, no stray `plugins/local` copy you still treat as “the” install, and a shim owned by the released/plugin path rather than a half-dead `dev` bake.

Check leftovers:

```bash
make localdev-status
stockroom doctor
```
