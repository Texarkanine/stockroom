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

1. [x] Write failing Cursor catalog assertions (TDD)
2. [x] Add Cursor marketplace entry for stockroom
3. [x] Write failing Claude catalog assertions (TDD)
4. [x] Add Claude marketplace entry for stockroom
5. [x] README discoverability assessment — left unchanged
6. [x] Commit on marketplace `stockroom` branch and open PR to `main` — https://github.com/Texarkanine/txrk9-agent-plugins/pull/2
7. [x] Memory-bank progress only in stockroom

## Technology Validation

No new technology - validation not required

## Dependencies

- Workspace checkout of `txrk9-agent-plugins` on branch `stockroom`
- `gh` authenticated for `Texarkanine/txrk9-agent-plugins`
- Stockroom plugin description sourced from existing plugin manifests

## Challenges & Mitigations

- **No test harness in marketplace repo**: Ephemeral parse/shape checks during build; live install deferred to m3.
- **Claude catalog asymmetry**: Left as-is; only added stockroom.
- **README**: Unchanged (URL-add docs; UI lists plugins).
- **Cross-repo commits**: Marketplace PR in `txrk9-agent-plugins`; memory-bank on stockroom `initialdev`.

## Preflight Findings

- **Amended (TDD encoding)**: Fail-then-implement cycles for Cursor and Claude catalog entries.
- **Advisory**: None blocking.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [x] QA