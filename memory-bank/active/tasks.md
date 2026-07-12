# Task: contributing-localdev-guide

* Task ID: contributing-localdev-guide
* Complexity: Level 3
* Type: enhancement (docs + Makefile atoms)

Bring Contributing to user-guide quality with a complete install → local checkout exclusive → verify → back path. Architecture/Advanced may only accrete rough notes. Creative: Hybrid thin Makefile atoms + narrative docs (`memory-bank/active/creative/creative-contributor-localdev-round-trip.md`).

## Pinned Info

### Contributor localdev round-trip

Why pinned: the whole deliverable is this lifecycle; every implementation step maps to Enter / Verify / Exit.

```mermaid
flowchart TD
  subgraph enter [Enter]
    Sync["make sync"] --> Torch["make torch"]
    Torch --> Shim["make shim TAKEOVER=1 if needed"]
    Shim --> Plugin["make plugin-local / claude --plugin-dir"]
    Shim --> Skills["optional: make localdev"]
  end
  subgraph verify [Verify]
    Gates["make ci / docs-build / reuse"]
    Doctor["stockroom doctor"]
  end
  subgraph exit [Exit]
    Clean["make localdev-clean"]
    RmPlugin["remove local plugin copy"]
    Rebake["rebake shim via marketplace plugin / sr-initialize"]
  end
  enter --> verify --> exit
```

## Component Analysis

### Affected Components

- **`docs/contributing/`**: development.md kitchen-sink → split lifecycle vs day-to-day; add local-workflow; keep licensing; update `.pages`
- **`CONTRIBUTING.md`**: funnel reorder — local-workflow first for hackers
- **Root `Makefile`**: add `localdev-clean`, optional `plugin-local`, `shim` passthrough for `TAKEOVER=1`; fix stale torch docs comment; `.PHONY` update
- **Cross-links**: `docs/user-guide/troubleshooting/index.md` points at Development for rsync — retarget to local-workflow where appropriate
- **`docs/architecture/` / `docs/advanced/`**: notes-only accretion if orphan content appears during TLC
- **Home / user-guide finished pages**: presentation-quality only — surgical link fixes, no WIP dumps

### Cross-Module Dependencies

- Makefile atoms → documented in local-workflow; development.md lists targets but does not own the lifecycle narrative
- `make shim` / takeover → existing `stockroom.shim` CLI (already tested); Make only wraps
- `plugin-local` rsync → Cursor local plugin path; session-start rectify on the *copy* must not steal a `dev` shim (documented nuance from session `aef4448b`)
- Torch operator SSOT remains `docs/user-guide/troubleshooting/torch.md`; Contributing links, does not fork

### Boundary Changes

- Public contributor interface: new Make targets + new/restructured docs pages (semver N/A; docs/dev UX)
- No engine API / schema changes
- No end-user install path changes

### Invariants & Constraints

- Must preserve: end users bootstrap via `sr-initialize`/marketplace only
- Must preserve: torch held out of lock; `make sync` strips torch; freeze under stockroom home
- Must preserve: shim baked-only succeed-or-refuse; `--takeover` only for dead foreign bakes
- Must hold: `make localdev` ≠ Cursor `plugins/local` (different surfaces)
- Must hold: finished Home/user-guide presentation-quality; Architecture/Advanced may be rough notes
- Non-goal: silent mega `contrib-enter` / fully scripted IDE reload or marketplace reinstall

## Open Questions

- [x] Enter/exit automation & Contributing IA → **Hybrid** (see `memory-bank/active/creative/creative-contributor-localdev-round-trip.md`)

## Test Plan (TDD)

### Behaviors to Verify

Docs / site (gates, not pytest):

- B1: `make docs-build` succeeds with new/renamed contributing pages and updated nav
- B2: CONTRIBUTING.md and user-guide troubleshooting links resolve to the correct contributing pages
- B3: local-workflow documents Enter / Verify / Exit with the hybrid atoms and human gates (reload, marketplace)
- B4: development.md no longer owns the lifecycle story (no competing SSOT)

Makefile atoms (manual / shell checks — no existing Makefile test harness; do not invent pytest theater):

- M1: `make localdev` then `make localdev-clean` → no `stockroom-local` symlinks; managed pre-commit marker block removed; idempotent second clean
- M2: `make plugin-local` (or chosen name) rsyncs to `~/.cursor/plugins/local/stockroom/` with excludes; `.cursor-plugin/plugin.json` present at destination (dry-run or DEST override for safety during CI-less verify)
- M3: `make shim TAKEOVER=1` passes `--takeover` to `shim install` (inspect recipe / dry command echo); default `make shim` does not

Engine (regression only if Make wrapper touches Python — expected: none):

- Existing shim takeover tests remain green if we only wrap CLI flags

### Test Infrastructure

- Framework: pytest under `skills/sr-search/tests/` for engine; properdocs `--strict` for docs; no Makefile unit suite
- New test files: **none** (Verification Plan style, matching prior docs L3)
- Integration: operator/manual checks M1–M3 on the build machine; full `make docs-build`; `make ci` only if Makefile/engine touch warrants (Make-only + docs: docs-build + reuse if needed)

### Integration Tests

- I1: Documented Enter recipe uses only named atoms + human steps (review against creative)
- I2: Exit recipe includes localdev-clean + plugin copy removal + shim rebake guidance

## Implementation Plan

1. **Makefile: `localdev-clean`**
    - Files: `Makefile`
    - Changes: remove `LOCAL_SKILLS_DIR` contents/symlinks; strip managed pre-commit marker block (mirror install awk); idempotent; help text
    - Creative ref: hybrid atoms

2. **Makefile: `plugin-local` + `shim` TAKEOVER passthrough + comment fix**
    - Files: `Makefile`
    - Changes: `plugin-local` rsync with documented excludes and overridable `PLUGIN_LOCAL_DEST`; `shim` accepts `TAKEOVER=1` → `--takeover`; fix stale `docs/contributor-guide/torch.md` comment → user-guide torch / contributing development
    - Creative ref: hybrid atoms

3. **Docs: add `docs/contributing/local-workflow.md`**
    - Files: new page
    - Changes: presentation-quality Enter / Verify / Exit; distinguish `localdev` vs `plugins/local` vs Claude `--plugin-dir`; footguns (torch after sync/ci, takeover, no symlink for Cursor plugin, third-party hooks toggle pointer to user-guide troubleshooting); link torch SSOT

4. **Docs: slim `development.md` + nav + CONTRIBUTING funnel**
    - Files: `docs/contributing/development.md`, `docs/contributing/.pages`, `CONTRIBUTING.md`
    - Changes: move lifecycle out of development; keep Makefile day-to-day, torch-safe contract, two uv projects, ad-hoc invocation; nav order local-workflow → development → licensing; CONTRIBUTING points hackers at local-workflow first

5. **Cross-links + notes sinks**
    - Files: `docs/user-guide/troubleshooting/index.md` (link retarget); optionally `docs/architecture/index.md` / `docs/advanced/index.md` for rough notes only if orphan content appears
    - Changes: surgical; no WIP on finished user-guide body copy beyond link targets

6. **Verification**
    - Run M1–M3 manual checks; `make docs-build`; `make reuse` if license-relevant paths touched; engine `make ci` only if Python changed (expected skip)

## Technology Validation

No new technology — validation not required. Makefile extensions use existing `rsync`/`awk`/`ln` already assumed by `localdev`.

## Challenges & Mitigations

- **`plugin-local` writes outside the repo**: Mitigate with overridable `PLUGIN_LOCAL_DEST`, document path clearly, never run destructive clean of marketplace installs from Make
- **`localdev-clean` vs user-edited pre-commit**: Mitigate by only removing the marked block (same markers as install)
- **Competing SSOTs** (development vs local-workflow): Mitigate by explicit page jobs in step 4; QA checklist for duplicate recipes
- **Exit path incomplete for marketplace**: Mitigate with honest prose — exit cannot fully automate marketplace reinstall; document “reinstall plugin + sessionStart rectify” / `sr-initialize` as human steps
- **Unrelated leftover creative** (`creative-embedding-invalidation.md`): Leave untouched

## Pre-Mortem

- **Plan fails because we still wrote a mega enter target**: Prevented by creative Decision + Implementation step 2 scoped to atoms only
- **Plan fails because docs stay kitchen-sink and nobody finds Exit**: Plan response — local-workflow is mandatory new page with Exit as first-class section; funnel updated in CONTRIBUTING
- **Plan fails because Make targets are untested and break pre-commit**: Already covered by Challenge on marked-block-only clean + M1 verification
- **Plan fails by dumping WIP into user-guide**: Constraint + step 5 surgical links only

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
