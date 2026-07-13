# Local Workflow

## Rip it Out

Do this once when you want the harness and on-path CLI to run **only** from your local checkout.

### 1. Make a Backup

Always back up your data before switching off of the normal plugin-marketplace install. Forward migrations can make it hard to go back to an older released engine against the same DB.

```bash
cp -r ~/.local/share/stockroom/warehouse.db ~/warehouse.db.backup
```

### 2. Uninstall the Plugin

Un-install the Stockroom plugin from your harness(es). Close the harnesses.

## Run a Local Checkout

Once you do not have an active Stockroom engine hooked into a harness, you're ready to hook up a local checkout.

### 1. Shim Takeover

```bash
make shim TAKEOVER=1 FORCE=1
```

Now, the `stockroom` CLI points at the engine in your local checkout. Python code changes you make *will* be reflected.

### 2. Harness Wiring

From the **repo root**, set `HARNESS` to the IDE you are entering with:

```bash
make sync                       # lock-faithful engine env (strips torch)
HARNESS=cursor make localdev    # or HARNESS=claude, etc
```

`HARNESS=… make localdev` composes three atoms, in order:

1. **`local-skills`**
	- Cursor: symlink `skills/*` into `.cursor/skills/stockroom-local/` (with a managed pre-commit guard so the mirror never lands in a commit).
	- Claude: no-op with a reminder to use `claude --plugin-dir .` for a session-scoped plugin load.
1. **`local-engine`** — claim the on-path shim as owner `dev` with `--takeover --force`, then `stockroom shim ensure-env` for this checkout’s engine dir (locked deps + torch from freeze).
2. **`local-dashboard`** — bounce `stockroom dashboard` (identity-aware replace).

### 3. Dashboard Start

Run `stockroom dashboard` to bounce the dashboard process to the new engine path.

### 4. Harness Reload

Re-open your harness.

If using Claude Code, launch with

```bash
claude --plugin-dir .
```

You should now have:

- `stockroom` on PATH with an engine path baked in pointing at this checkout (owner `dev`)
- For Cursor: `/sr-*` skills resolving to the checkout mirror when working in this project

## Verify

```bash
make localdev-status    # read-only status report
stockroom doctor smoke  # ensure Torch actually works
```

Confirm your harness is loading **this** checkout’s skills, not a leftover marketplace install.

You are now ready to start developing!

## Done Developing

Undo localdev-managed bits and clear the live `dev` shim claim:

```bash
HARNESS=cursor make localdev-clean    # or HARNESS=claude
```

That removes the Cursor skills mirror / pre-commit guard (Claude: nothing to mirror) and **deletes `~/.local/bin/stockroom` only if its header says `owner=dev`**. Harness-owned shims are left alone. Warehouse and marketplace installs are untouched.

`stockroom` is now off PATH on purpose. SessionStart `shim rectify` will **not** recreate it (rectify never creates a missing shim). Finish exit like this:

1. Reinstall / enable the marketplace plugin in the harness UI.
2. Launch the harness so plugin hooks and skills load.
3. Run [`sr-initialize`](../user-guide/quickstart.md) once — if torch/schedule/env are already fine it should mostly just bind the on-path shim for the plugin.

Then confirm:

```bash
make localdev-status
stockroom doctor
```

Goal: no leftover skills mirror (Cursor), and a shim owned by the released/plugin path — not a half-dead `dev` bake.

## Appendix: Modular Atoms

Use these when you do not need the full rip-it-out path. Harness-scoped targets require `HARNESS=cursor` or `HARNESS=claude` and error if unset or invalid.

| Target | `HARNESS`? | Role |
| --- | --- | --- |
| `local-skills` | required | Wire checkout skills for that harness |
| `local-engine` | no | `shim TAKEOVER=1 FORCE=1` + `ensure-env` |
| `local-dashboard` | no | Bounce `stockroom dashboard` |
| `localdev` | required | Invokes the three atoms above |
| `localdev-clean` | required | Undo harness-managed bits + remove `owner=dev` shim (not warehouse) |
| `localdev-status` | optional | Report managed vs shim sections |

### Engine-only shim claim

```bash
make shim                      # bake this checkout (owner: dev)
make shim TAKEOVER=1           # replace a *dead* foreign bake
make shim TAKEOVER=1 FORCE=1   # replace a *live* foreign bake (dangerous)
# or:
make local-engine              # takeover+force + ensure-env (no HARNESS)
```

`FORCE=1` is for localdev and recovery of a broken install. It is not the agent default — skills and initialize must not recommend it casually. Prefer `HARNESS=… make localdev` when you want skills + engine + dashboard together.

### Status semantics

`make localdev-status` prints two sections (read-only; no mutations):

1. **localdev-managed** — skills mirror and pre-commit block (when present)
2. **shim** — on-PATH location, default dest (`~/.local/bin/stockroom`), owner + baked `app-dir` from the shim header, whether that engine dir is alive, and torch version in that engine’s `.venv` (or “not installed”)

### Clean semantics

`HARNESS=… make localdev-clean` removes that harness’s localdev-managed artifacts (Cursor skills mirror + pre-commit block; Claude has none) and deletes `~/.local/bin/stockroom` **only when** the shim header is `owner=dev`. It does **not** touch the warehouse, marketplace installs, or a harness-owned (`cursor` / `claude`) shim. After a `dev` unclaim, reinstall the plugin, launch, and run `sr-initialize` once to bind a normal shim — rectify alone will not recreate it.

### Claude without marketplace

For a session-scoped Claude load of the whole plugin tree (skills + committed plugin hooks):

```bash
claude --plugin-dir /path/to/stockroom
```

`HARNESS=claude make local-skills` prints that reminder and does not create a Cursor-style skills mirror.

### Hooks when changing the bootstrap surface

Committed plugin hooks under `hooks/*.json` use `CURSOR_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT`. After you uninstall the marketplace plugin those variables are unset, so copying those files into the project does **not** restore sessionStart. Make does not install project hooks. Only edit hooks by hand if you are changing the hook bootstrap surface itself; for day-to-day localdev, use `local-dashboard` / `stockroom dashboard`.

### Enter footguns

- **`make sync` / `make ci` strips torch.** Restore with `stockroom shim ensure-env` (hashed freeze) — not `make torch`, which picks `TORCH_INDEX` and rewrites the freeze. Use `make torch` only when deliberately choosing/changing the accepted stack ([Development](development.md), [Torch](../user-guide/troubleshooting/torch.md)).
- **Shim is succeed-or-refuse.** It never guesses an engine location. `TAKEOVER=1` alone is for dead foreign bakes; live foreign needs `TAKEOVER=1 FORCE=1`.
- **Always backup the warehouse** before enter (see Rip It Out).
- **Marketplace plugin must be uninstalled** so the next harness launch in this repo uses project wiring, not the old plugin root.
- **`HARNESS` is required** for `local-skills`, `localdev`, and `localdev-clean`.
