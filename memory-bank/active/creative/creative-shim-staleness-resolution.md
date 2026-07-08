# Algorithm Decision: Shim Staleness Healing (Revised)

> **Supersedes** the 2026-07-08 "always-scan, version-ranked" decision (see git history of this file). The operator vetoed all runtime self-resolution with a hard constraint: **the shim must either succeed correctly or refuse to run — never guess.** The scan design also had two structural defects the operator identified: (1) its root list encoded harness cache layouts, requiring maintenance every time a harness/layout is added; (2) ranking by a version string read from glob-matched directories is a supply-chain injection surface — anything that can drop a plausible directory into a cache path could claim the highest version and capture every future invocation.

## Problem

The generated `~/.local/bin/stockroom` shim carries a baked `APP_DIR`. Harness plugin caches are versioned per release: an update creates a new directory and the old one is eventually pruned (Claude Code documents ~7 days retention of the previous version's directory). Additionally, the same plugin may be installed **independently in two harnesses on one machine**. The shim must always exec a correct engine — with no runtime guessing — and the two-harness case must have a deterministic owner.

**Hard constraints** (operator, 2026-07-08):

- No runtime self-resolution: the shim never scans, ranks, or picks among candidates. Succeed-correctly-or-refuse.
- No harness-layout knowledge baked anywhere (no root lists to maintain).
- The write path for the shim must not be triggerable by ambient filesystem state (supply-chain posture).

**Verified facts:**

- Both harnesses hand plugin-delivered hooks the authoritative current install root: Cursor substitutes/exports `CURSOR_PLUGIN_ROOT` ([docs](https://cursor.com/docs/hooks.md); confirmed by Cursor staff and by cursor-warehouse's live `hooks.json` on this machine); Claude Code substitutes/exports `CLAUDE_PLUGIN_ROOT` ([docs](https://code.claude.com/docs/en/hooks)), which "changes on each plugin update."
- Claude retains the previous version's cache dir ~7 days post-update; Cursor's retention is undocumented (old dirs observed to linger on this machine).
- Cursor `sessionStart` hooks are fire-and-forget (non-blocking); both harnesses support per-hook timeouts.

## Options Evaluated

- **A — Always-scan, version-ranked** (the superseded decision): vetoed — runtime guessing, layout coupling, injection surface.
- **B — Baked-only shim + session-start hook rectification + ownership**: shim verifies its baked dir and execs or refuses; a plugin sessionStart hook in each harness invokes the engine (at the harness-provided root) to re-bake the shim when it is the owner and the baked path is stale.
- **C — Baked-only shim + manual re-init only**: no hook; a stale shim refuses until the user re-runs `sr-initialize`.

## Analysis

B and C share the correct shim (dumb, static, succeed-or-refuse). They differ only in who heals it and when:

- **C** makes every plugin update a user-visible breakage once the old cache dir is pruned ("stockroom stopped working, run sr-initialize again") — recurring manual toil that contradicts the phase's one-command promise.
- **B** heals at the next session start of the owning harness, using a root the harness itself delivered — zero guessing, zero layout knowledge, and the healing window is bounded (old dir keeps working meanwhile; if already pruned, the shim refuses cleanly with the remedy rather than misbehaving).
- Two-harness resolution requires ownership in either case; B needs it to prevent hook flapping (last-session-wins version churn between harnesses), C needs it to prevent init fights. Ownership marker + single-writer discipline solves both identically.

Key insights:

- The env-var-delivered root removes layout knowledge from *every* component: the shim has none, the rectify logic receives its root as an argument, and only the hook wiring (`${*_PLUGIN_ROOT}` in committed `hooks.json`) touches harness specifics — which is exactly the artifact each harness defines that variable for.
- The write path is now: harness (trusted) → plugin-shipped hook (versioned, reviewed) → tested engine code → `~/.local/bin`. No ambient directory can trigger or influence a write.
- `systemPatterns.md` hook discipline ("session-start hook *only* launches the dashboard") is amended by this decision (operator-sanctioned) to: launches the dashboard *and* rectifies the shim — still never ingests, never migrates, never errors, never blocks.

## Decision

**Selected**: Option B — baked-only succeed-or-refuse shim, session-start hook rectification, explicit ownership.

**Rationale**: the only design satisfying the hard no-guessing constraint that also keeps plugin updates invisible to the user. It eliminates layout coupling and the injection surface identified by the operator, and gives the two-harness case a deterministic single writer.

**Tradeoff**: a bounded window (update → next owning-harness session start) where the shim runs the owner's previous, still-on-disk install — deterministic and version-labeled, never incorrect resolution; if the old dir is already gone, a clean refusal with remedy. Accepted by the operator ("a wink of a possible window — if any").

## Implementation Notes

- **Shim runtime** (entire logic): `uv` on PATH or one-line error (exit 127); baked `APP_DIR/pyproject.toml` exists or one-line error naming the remedy (`sr-initialize` / next session start; `make shim` for dev-owned shims); else `PYTHONPATH="$APP_DIR/src" exec uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom "$@"`.
- **Header markers** (machine-readable, single-line): `# STOCKROOM_OWNER=<cursor|claude|dev>` and `# STOCKROOM_APP_DIR=<path>` plus the generator version stamp.
- **Ownership policy** (lives in tested Python, `stockroom.shim`):
  - *install* (driven by `sr-initialize` / `make shim`): dest absent → write with invoker's owner label. Dest present, same owner → rewrite. Dest present, different owner, baked dir **alive** → refuse with explanation. Different owner, baked dir **dead** → takeover permitted (`--takeover` flag so the action is explicit).
  - *rectify* (driven by the sessionStart hook): only acts when dest exists **and** owner matches **and** rendered content differs (covers both a moved root and a template change shipped in an update); otherwise silent no-op. Never creates a missing shim — installation requires the explicit init/dev gate.
- **Hook wiring**: dual hook configs mirroring the dual-manifest pattern (Cursor `hooks.json` schema ≠ Claude schema): each invokes the engine at `${CURSOR_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_ROOT}` with `shim rectify --owner <harness>`, output silenced, failures swallowed (hook discipline: never errors, never blocks), short timeout.
- **Update propagation**: the hook ships in the plugin, so a plugin update simultaneously updates the engine, the template, and the hook that re-bakes with them — lockstep by construction.
- **Dev mode**: `make shim` installs with owner `dev` baking the checkout; harness hooks never touch it (owner mismatch). Dev shims heal only via `make shim`.
