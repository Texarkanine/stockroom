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

From the **repo root**:

```bash
make sync          # lock-faithful engine env (strips torch)
make torch         # reinstall torch out-of-band + freeze under stockroom home
make localdev      # skills + PATH hooks + shim claim + ensure-env + dashboard bounce
```

`make localdev` does, in order:

1. Symlink `skills/*` into `.cursor/skills/stockroom-local/` (with a managed pre-commit guard so the mirror never lands in a commit).
2. Install **PATH-based** project hooks (Cursor: `.cursor/hooks.json`; Claude: `.claude/settings.local.json`) that call on-path `stockroom` — no `PLUGIN_ROOT`.
3. Claim the on-path shim as owner `dev` with `--takeover --force` (replaces a live foreign bake — deliberate two-key turn).
4. Run `stockroom shim ensure-env` for this checkout’s engine dir.
5. Bounce `stockroom dashboard`.

Reload the Cursor window (or start Claude in this repo) so skills and project hooks load. Cursor project hooks may be experiment-gated on some builds; if sessionStart never fires, the dashboard is still reachable via CLI after the localdev bounce — see [Troubleshooting](../user-guide/troubleshooting/index.md#cursor-hooks--auto-dashboard-never-fire).

You should now have:

- `stockroom` on PATH baking this checkout (owner `dev`)
- `/sr-*` skills resolving to the checkout mirror when working in this project
- sessionStart (when enabled) rectifying the shim and starting the dashboard

## Verify

```bash
make localdev-status   # localdev-managed vs shim sections (read-only)
stockroom doctor       # bake, owner, env health
make ci                # engine gate (re-run make torch afterward if you need embeddings)
make docs-build        # when docs change
make reuse             # when licensing-relevant paths change
```

Confirm the harness is loading **this** checkout’s skills/hooks, not a leftover marketplace install.

## Exit

Undo only what localdev managed, then restore a normal install:

```bash
make localdev-clean    # skills mirror, managed hooks, pre-commit block (idempotent; not warehouse)
```

Then get a normal on-path shim again:

- Reinstall / enable the marketplace plugin and let session-start `shim rectify` rebake, **or**
- Re-run [`sr-initialize`](../user-guide/quickstart.md) (re-probes; only does what is still missing).

Exit cannot fully automate marketplace UI reinstall or IDE reload — those stay human steps. Goal: no leftover skills mirror or managed project hooks, and a shim owned by the released/plugin path rather than a half-dead `dev` bake.

```bash
make localdev-status
stockroom doctor
```

## Appendix: Modular Bits

Use these when you do not need the full rip-it-out path.

### Engine-only shim claim

```bash
make shim                      # bake this checkout (owner: dev)
make shim TAKEOVER=1           # replace a *dead* foreign bake
make shim TAKEOVER=1 FORCE=1   # replace a *live* foreign bake (dangerous)
```

`FORCE=1` is for localdev and recovery of a broken install. It is not the agent default — skills and initialize must not recommend it casually. Prefer the one-shot `make localdev` when you want skills + hooks + claim together.

### Status semantics

`make localdev-status` prints two sections:

1. **localdev-managed** — skills mirror, Cursor/Claude managed hook markers, pre-commit block
2. **shim** — pointer to `stockroom doctor` / `stockroom shim --help` (make does not mutate here)

### Clean semantics

`make localdev-clean` removes only localdev-managed artifacts. It does **not** touch the warehouse, marketplace installs, or the on-path shim.

### Claude without marketplace

For a session-scoped Claude load of the whole plugin tree (skills + committed plugin hooks):

```bash
claude --plugin-dir /path/to/stockroom
```

`make localdev` still writes Claude `settings.local.json` SessionStart hooks for this project; use `--plugin-dir` when you also need the packaged plugin surface outside the localdev mirror.

### Enter footguns

- **`make sync` / `make ci` strips torch.** Re-run `make torch` before embed/semantic work. Operator contract: [Torch](../user-guide/troubleshooting/torch.md).
- **Shim is succeed-or-refuse.** It never guesses an engine location. `TAKEOVER=1` alone is for dead foreign bakes; live foreign needs `TAKEOVER=1 FORCE=1`.
- **Always backup the warehouse** before enter (see Rip It Out).
- **Marketplace plugin must be uninstalled** so the next harness launch in this repo uses project wiring, not the old plugin root.
