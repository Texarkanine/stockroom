# Project Brief

## User Story

As the stockroom operator, I want Phase 5 — Distribution and Release — completed so that a fresh user can add the `txrk9-agent-plugins` marketplace, install stockroom, run `sr-initialize`, and use all four surfaces against their own Cursor and Claude Code history — the v1 success criteria, demonstrated end to end.

## Use-Case(s)

### Use-Case 1 — Manual install from docs

A user follows install/usage documentation, installs the dual-manifest plugin manually (without the marketplace), and can invoke skills with the correct per-harness forms (`/sr-*` in Cursor; `<plugin>:<skill>` in Claude Code).

### Use-Case 2 — Marketplace install

A user adds `https://github.com/Texarkanine/txrk9-agent-plugins`, installs stockroom from both Cursor and Claude marketplace entries, and gets the same plugin pointing at the source repo.

### Use-Case 3 — Released spine on a clean machine

After release-please cuts a versioned release (version synced into both plugin manifests), a clean-machine install from the marketplace runs `sr-initialize` and successfully uses `sr-search` / `sr-semantic` / `sr-query` / `sr-dashboard` against real Cursor and Claude Code history.

## Requirements

1. **Plugin definition + install docs** — user-facing install and usage documentation (marketplace path + local/dev loaders); per-harness skill-invocation forms documented from platform contracts (`/sr-*` vs Claude's `/stockroom:<skill>`). Live marketplace install and empirical invocation proof deferred to m2/m3 (catalog + `main`). Manifests already exist from Phase 0. No CI pins on doc prose — docs may move freely.
2. **Marketplace entry** — stockroom added to `txrk9-agent-plugins` in both `.cursor-plugin/marketplace.json` and `.claude-plugin/marketplace.json`, pointing at the GitHub source repo (follow the existing `slobac` / `cursor-warehouse` entry pattern).
3. **Release flow + end-to-end install test** — exercise the release-please path (version synced into both plugin manifests, not marketplace manifests); then prove the full spine on a clean machine: marketplace add → install → `sr-initialize` → all four surfaces against real data.
4. Cross-harness correctness must follow official docs ([Cursor Plugins](https://cursor.com/docs/plugins), [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference.md)) and the working example at `../slobac`.

## Constraints

1. Scope is Phase 5 of `planning/roadmap.md` only — no post-v1 work (recap, additional harnesses, etc.).
2. Engine invocation is already uniform via on-path `stockroom`; only skill-invocation forms remain harness-specific to verify.
3. Marketplace lives in the separate `txrk9-agent-plugins` repo; plugin versioning stays in stockroom's release-please config (already wired in Phase 0).
4. Dual-manifest template: committed layout = install layout; no build step.
5. Follow `slobac` as the cross-harness plugin reference for manifests, marketplace entries, and install-doc shape.

## Acceptance Criteria

1. Install/usage docs exist and document the empirically verified per-harness invocation forms.
2. Stockroom appears in both Cursor and Claude marketplace manifests in `txrk9-agent-plugins`, pointing at `Texarkanine/stockroom`.
3. Release-please successfully syncs a version into both `.cursor-plugin/plugin.json` and `.claude-plugin/plugin.json`.
4. A clean-machine marketplace install demonstrates: `sr-initialize` + all four surfaces working against real Cursor and Claude Code history.
5. Roadmap Phase 5 milestones can be checked off; v1 "clean enough to ship" gate is met.
