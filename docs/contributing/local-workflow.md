# Local Workflow

The contributor round-trip: leave a normal install, hack exclusively from this checkout, verify, and return to the released/plugin install without a hybrid half-state.

End users stay on [`sr-initialize`](../user-guide/quickstart.md) / the marketplace. The Makefile is the **checkout** entrypoint — not an alternate bootstrap for operators who only want Stockroom installed.

Day-to-day targets, the torch-safe `uv` contract, and ad-hoc engine invocation live in [Development](development.md).

## Rip It Out

Do this once when you want the harness and on-path CLI to run **only** from this checkout.

### 1. Backup the warehouse

Always back up before enter. Forward migrations can make it hard to go back to an older released engine against the same DB.

```bash
cp -a ~/.local/share/stockroom/warehouse.db ~/warehouse.db.backup
```

(Adjust the path if you set `STOCKROOM_HOME`.)

### 2. Uninstall the marketplace plugin

Uninstall Stockroom from every harness you use (Cursor / Claude Code plugin UI). Close those harness windows so plugin hooks are not still firing against the old install.

### 3. Stop using the old dashboard listener

There is no `stockroom dashboard stop` subcommand. Close harnesses that would relaunch it, then either leave an old listener alone for `make localdev` to bounce via identity-aware replace, or kill the process bound to the dashboard port if you want a clean slate.

### 4. Wire the checkout

From the **repo root**, set `HARNESS` to the IDE you are entering with:

```bash
make sync                       # lock-faithful engine env (strips torch)
make torch                      # reinstall torch out-of-band + freeze under stockroom home
HARNESS=cursor make localdev    # or HARNESS=claude
```

`HARNESS=… make localdev` composes three atoms, in order:

1. **`local-skills`** — Cursor: symlink `skills/*` into `.cursor/skills/stockroom-local/` (with a managed pre-commit guard so the mirror never lands in a commit). Claude: no-op with a reminder to use `claude --plugin-dir` for a session-scoped plugin load.
2. **`local-engine`** — claim the on-path shim as owner `dev` with `--takeover --force`, then `stockroom shim ensure-env` for this checkout’s engine dir.
3. **`local-dashboard`** — bounce `stockroom dashboard` (identity-aware replace).

Reload the Cursor window (or start Claude in this repo) so checkout skills load. Marketplace/plugin sessionStart hooks are gone after uninstall; the dashboard is still reachable via the localdev bounce or `stockroom dashboard` — see [Troubleshooting](../user-guide/troubleshooting/index.md#cursor-hooks--auto-dashboard-never-fire).

You should now have:

- `stockroom` on PATH baking this checkout (owner `dev`)
- For Cursor: `/sr-*` skills resolving to the checkout mirror when working in this project
- Dashboard bounced once at enter

## Verify

```bash
make localdev-status            # localdev-managed vs shim sections (read-only)
stockroom doctor                # bake, owner, env health
make ci                         # engine gate (re-run make torch afterward if you need embeddings)
make docs-build                 # when docs change
make reuse                      # when licensing-relevant paths change
```

Confirm the harness is loading **this** checkout’s skills, not a leftover marketplace install.

## Exit

Undo only what localdev managed for that harness, then restore a normal install:

```bash
HARNESS=cursor make localdev-clean    # or HARNESS=claude
```

Then get a normal on-path shim again:

- Reinstall / enable the marketplace plugin and let session-start `shim rectify` rebake, **or**
- Re-run [`sr-initialize`](../user-guide/quickstart.md) (re-probes; only does what is still missing).

Exit cannot fully automate marketplace UI reinstall or IDE reload — those stay human steps. Goal: no leftover skills mirror (Cursor), and a shim owned by the released/plugin path rather than a half-dead `dev` bake.

```bash
make localdev-status
stockroom doctor
```

## Appendix: Modular Atoms

Use these when you do not need the full rip-it-out path. Harness-scoped targets require `HARNESS=cursor` or `HARNESS=claude` and error if unset or invalid.

| Target | `HARNESS`? | Role |
| --- | --- | --- |
| `local-skills` | required | Wire checkout skills for that harness |
| `local-engine` | no | `shim TAKEOVER=1 FORCE=1` + `ensure-env` |
| `local-dashboard` | no | Bounce `stockroom dashboard` |
| `localdev` | required | Invokes the three atoms above |
| `localdev-clean` | required | Undo that harness’s managed bits (not warehouse/shim) |
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

`make localdev-status` prints two sections:

1. **localdev-managed** — skills mirror and pre-commit block (when present)
2. **shim** — pointer to `stockroom doctor` / `stockroom shim --help` (make does not mutate here)

### Clean semantics

`HARNESS=… make localdev-clean` removes only that harness’s localdev-managed artifacts. It does **not** touch the warehouse, marketplace installs, or the on-path shim.

### Claude without marketplace

For a session-scoped Claude load of the whole plugin tree (skills + committed plugin hooks):

```bash
claude --plugin-dir /path/to/stockroom
```

`HARNESS=claude make local-skills` prints that reminder and does not create a Cursor-style skills mirror.

### Hooks when changing the bootstrap surface

Committed plugin hooks under `hooks/*.json` use `CURSOR_PLUGIN_ROOT` / `CLAUDE_PLUGIN_ROOT`. After you uninstall the marketplace plugin those variables are unset, so copying those files into the project does **not** restore sessionStart. Make does not install project hooks. Only edit hooks by hand if you are changing the hook bootstrap surface itself; for day-to-day localdev, use `local-dashboard` / `stockroom dashboard`.

### Enter footguns

- **`make sync` / `make ci` strips torch.** Re-run `make torch` before embed/semantic work. Operator contract: [Torch](../user-guide/troubleshooting/torch.md).
- **Shim is succeed-or-refuse.** It never guesses an engine location. `TAKEOVER=1` alone is for dead foreign bakes; live foreign needs `TAKEOVER=1 FORCE=1`.
- **Always backup the warehouse** before enter (see Rip It Out).
- **Marketplace plugin must be uninstalled** so the next harness launch in this repo uses project wiring, not the old plugin root.
- **`HARNESS` is required** for `local-skills`, `localdev`, and `localdev-clean`.
