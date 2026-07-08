# Algorithm Decision: Shim Staleness Detection & Resolution Order

## Problem

The generated `~/.local/bin/stockroom` shim carries a baked `APP_DIR` (the engine directory inside a harness plugin cache). Harness caches are **versioned per release** — an update creates a *new* cache directory and the old one may or may not be pruned. The shim must, on every invocation, end up exec-ing the *current* install, deterministically, even when:

1. the baked directory has been deleted (plugin updated, old dir pruned);
2. the baked directory **still exists but a newer install exists elsewhere** (old dir lingers — the unresolved TODO in `planning/brainstorm/stockroom-on-path-cli.md`);
3. multiple harness caches coexist (Cursor and Claude both have the plugin, possibly at different versions);
4. a local/dev install coexists with marketplace installs.

**Inputs** (verified empirically on this machine):

- Cursor installs: `~/.cursor/plugins/cache/<marketplace>/<plugin>/<git-sha>/` (sha dirs — no version ordering in the path) and `~/.cursor/plugins/local/<plugin>/` (unversioned dev installs). `~/.cursor/plugins/marketplaces/` holds marketplace *clones*, not installs — out of scope.
- Claude installs: `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`; `~/.claude/plugins/installed_plugins.json` records the authoritative `installPath` per plugin (including local installs that point into the Cursor tree).
- Every install root carries the dual manifests (`.cursor-plugin/plugin.json` / `.claude-plugin/plugin.json`) whose `"version"` field release-please keeps current. The engine `pyproject.toml` version is static (`0.0.0`) — **not** a version signal.
- No harness env var (`CURSOR_PLUGIN_ROOT`) exists at shim runtime — cron and bare shells invoke it.
- Cost measurements: bounded glob over the candidate roots ≈ 6 ms; unbounded `find -L` over both plugin trees ≈ 2.2 s cold. A per-invocation bounded scan is free; a per-invocation `find` is not.

**Requirements**: correct (never silently runs an outdated engine), deterministic, fast on the hot path, self-healing without re-running `sr-initialize`, and implementable in dumb POSIX sh (all *product* logic stays in the tested Python dispatcher — the shim may only *select a directory*).

**Invariant**: whatever is selected is exec'd through the torch-safe contract (`PYTHONPATH="$APP_DIR/src" exec uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom "$@"`).

## Options Evaluated

- **A — Bake + existence check + `find` fallback** (the original brainstorm sketch): use the baked dir if `pyproject.toml` exists, else `find -L` the caches.
- **B — Always re-resolve by newest mtime**: ignore the bake except as a last resort; bounded-glob all candidate roots each run and pick the most recently modified.
- **C — Always-scan, version-ranked, baked-preferred on ties**: bounded-glob a fixed ordered root list each run; read each candidate's plugin-manifest `"version"`; pick the highest version (`sort -V`), preferring the baked dir when it ties for the top.
- **D — Consult harness install manifests**: parse `installed_plugins.json` (Claude) and whatever Cursor's equivalent is to find the authoritative install path.

## Analysis

| Criterion | A: exist-check | B: newest mtime | C: version-ranked | D: harness manifests |
|-----------|----------------|-----------------|-------------------|----------------------|
| Correctness | ✗ fails case 2 (lingering old dir pins forever) | ~ mtime is a proxy; any touch in an old cache mis-ranks it; local dev churn always "wins" | ✓ version is the actual semantic being asked about | ✓ for Claude; ✗ Cursor has no verified equivalent manifest |
| Determinism | ✓ (but deterministically wrong in case 2) | ~ ties/frivolous mtimes | ✓ version, then fixed root order | ~ two different mechanisms |
| Hot-path speed | fast happy path, 2.2 s `find` on miss | ~6 ms | ~6 ms + one `grep` per candidate (few) | JSON parsing in sh |
| Shim dumbness | ✓ | ✓ | ✓ selection only: glob + grep + `sort -V` | ✗ per-harness JSON schemas in sh |

Key insights:

- Case 2 is the entire reason this decision was reserved to m2 — **any design whose fast path is "baked dir still exists" is wrong**, because existence does not imply currency. That eliminates A as-is.
- Because the bounded scan costs ~6 ms, the "fast path vs. healing path" dichotomy is false: the shim can afford to *re-derive the answer on every invocation* and use the baked path only as a preference/fallback, which is structurally self-healing.
- Version-from-manifest is the only candidate signal that is uniform across all install shapes (Cursor sha dirs, Claude version dirs, local installs) *and* semantically means "newer release". The sha in Cursor's path and the mtime on disk do not.
- All candidate roots are `~`-relative, so the rendered shim is testable end-to-end by running it as a subprocess with `HOME` pointed at a fixture tree — no injection seams needed in the template.

## Decision

**Selected**: Option C — always-scan, version-ranked, baked-preferred on ties.

**Rationale**: it is the only option that is correct in all four scenarios (including the lingering-old-dir case that motivated the milestone), stays deterministic (version rank, then baked preference, then fixed root order), keeps the hot path in single-digit milliseconds, and keeps the shim's job to *directory selection only* — no product logic, no JSON schemas, just glob + `grep` + `sort -V`.

**Tradeoff**: the shim does slightly more work per invocation than a bare existence check (~6 ms — negligible against uv+python startup), and it greps a JSON field with a line-oriented tool (accepted: the manifest is machine-written, one `"version": "…"` per file; a malformed candidate simply ranks last rather than failing the run).

## Implementation Notes

- **Fixed scan roots** (ordered; the order is the final tiebreak):
  1. `~/.cursor/plugins/local/stockroom/skills/sr-search` (deliberate dev install)
  2. `~/.cursor/plugins/cache/*/stockroom/*/skills/sr-search`
  3. `~/.claude/plugins/cache/*/stockroom/*/skills/sr-search`
- **Candidate validity**: `pyproject.toml` present in the candidate `sr-search` dir. Version read from the plugin root two levels up (`.cursor-plugin/plugin.json`, falling back to `.claude-plugin/plugin.json`), via `grep -m1 '"version"'` + `sed`; unreadable version ranks as `0`.
- **Selection**: highest version wins (`sort -V`); if the baked `APP_DIR` is among the max-version candidates, prefer it (it records the generating harness — the brainstorm's stated preference); otherwise first max-version candidate in root order.
- **Empty scan**: fall back to the baked `APP_DIR` if it is valid (covers cache layouts this shim's glob list doesn't know); if that also fails, exit with a one-line error telling the user to re-run `sr-initialize`.
- **`uv` missing**: checked before exec; one clear line (`stockroom: uv not found — see sr-initialize prerequisites`), nonzero exit — never a bare shell error.
- **Dev-pinned variant** (interacts with the Q2 decision): a shim generated for a repo checkout (`make shim`) must *not* re-resolve away to a higher-versioned cache install — it is pinned to the checkout and errors if the checkout is gone. The template takes this as a render-time mode.
- **Install-time verify** (the other half of "bake-then-verify"): after writing the shim, the generator runs `stockroom --version` through PATH and checks it answers — the m1 `--version` probe exists precisely for this. Runtime never invokes `--version` (that would cost a full uv+python startup per run).
