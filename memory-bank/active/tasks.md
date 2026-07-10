# Task: p5-m2-marketplace-entries

* Task ID: p5-m2-marketplace-entries
* Complexity: Level 2
* Type: simple enhancement

Add `stockroom` to both marketplace manifests in `Texarkanine/txrk9-agent-plugins` (workspace checkout on branch `stockroom`), pointing at `Texarkanine/stockroom` in the same shape as existing `slobac` / `cursor-warehouse` entries. Open a PR from that branch. Live install proof remains m3.


## Test Plan (TDD)

### Behaviors to Verify

- [Cursor catalog includes stockroom]: parse `.cursor-plugin/marketplace.json` → a plugin object with `name` `"stockroom"`, `source.source` `"github"`, `source.repo` `"Texarkanine/stockroom"`, and a non-empty `description`
- [Claude catalog includes stockroom]: parse `.claude-plugin/marketplace.json` → same shape for `stockroom`
- [No version pin]: neither marketplace entry includes a stockroom version field (L4 invariant: versioning stays in stockroom plugin manifests)
- [Existing entries preserved]: `slobac` (both) and `cursor-warehouse` (Cursor) remain unchanged
- [Valid JSON]: both marketplace files remain parseable JSON after edit
- [PR opened]: a pull request exists from `stockroom` → `main` on `Texarkanine/txrk9-agent-plugins` describing the catalog addition

### Test Infrastructure

- Framework: **none** in `txrk9-agent-plugins` (JSON + README only; no CI, no test runner)
- Stockroom's pytest suite does not own the marketplace repo and must not grow cross-repo catalog pins (m1 precedent: no docstring/prose CI pins; L4 invariant: marketplace never carries a stockroom version pin)
- Conventions: verification is a small ephemeral assert script run during build (JSON parse + field assertions), not a committed harness
- New test files: **none committed** — ephemeral assert helper during build; durable proof is the PR + m3 clean-machine install

## Implementation Plan

1. Write failing Cursor catalog assertions (TDD)
   - Files: ephemeral assert (shell/`python -c` against `.cursor-plugin/marketplace.json`)
   - Changes: assert stockroom entry missing → expect failure; also snapshot `slobac` / `cursor-warehouse` for later preservation checks
2. Add Cursor marketplace entry for stockroom
   - Files: `/home/mobaxterm/git/txrk9-agent-plugins/.cursor-plugin/marketplace.json`
   - Changes: append `{"name": "stockroom", "source": {"source": "github", "repo": "Texarkanine/stockroom"}, "description": "Local, faithful, searchable warehouse of your agentic-coding history."}` (description from stockroom plugin manifests); re-run Cursor assertions → pass; confirm no `version` key; confirm prior entries unchanged
3. Write failing Claude catalog assertions (TDD)
   - Files: ephemeral assert against `.claude-plugin/marketplace.json`
   - Changes: assert stockroom entry missing → expect failure; snapshot `slobac`
4. Add Claude marketplace entry for stockroom
   - Files: `/home/mobaxterm/git/txrk9-agent-plugins/.claude-plugin/marketplace.json`
   - Changes: append same-shaped entry (do **not** backfill `cursor-warehouse`); re-run Claude assertions → pass; confirm no `version` key; confirm `slobac` unchanged
5. README discoverability assessment
   - Files: `/home/mobaxterm/git/txrk9-agent-plugins/README.md`
   - Changes: **none expected** — README documents how to add the marketplace URL; the catalog UI is the plugin list. Only edit if a minimal plugin inventory is clearly warranted; default leave as-is
6. Commit on marketplace `stockroom` branch and open PR to `main`
   - Conventional commit (e.g. `feat: add stockroom to Cursor and Claude marketplaces`)
   - Push `-u` and `gh pr create` from `stockroom` → `main` with summary + test plan; verify PR exists
7. Memory-bank progress only in stockroom (this L4 parent) — no marketplace code changes in the stockroom repo beyond ephemeral tracking

## Technology Validation

No new technology - validation not required

## Dependencies

- Workspace checkout of `txrk9-agent-plugins` on branch `stockroom` (already present, clean, at `main` tip)
- `gh` authenticated for `Texarkanine/txrk9-agent-plugins`
- Stockroom plugin description sourced from existing `.cursor-plugin/plugin.json` / `.claude-plugin/plugin.json` (already identical)

## Challenges & Mitigations

- **No test harness in marketplace repo**: Do not invent a committed one; verify with ephemeral parse/shape checks during build and PR review. Live install deferred to m3.
- **Claude catalog asymmetry** (`cursor-warehouse` missing): Leave as-is; only add stockroom.
- **README "if needed"**: Prefer no README change; marketplace UI is the discoverability surface after the URL is added.
- **Cross-repo commits**: Marketplace changes commit/PR in `txrk9-agent-plugins`; stockroom memory-bank commits stay on stockroom `initialdev`.
- **Branch already named `stockroom` but empty of commits ahead of main**: First commit on this branch will be the catalog addition; push `-u` then open PR.

## Preflight Findings

- **Amended (TDD encoding)**: Split Cursor/Claude work into fail-then-implement cycles (steps 1–4). Prior plan listed production edits before verification.
- **Advisory**: None blocking. Optional future: list plugins in marketplace README — out of default plan.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [ ] Build
- [ ] QA
