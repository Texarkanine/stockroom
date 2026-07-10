# E2E Clean-Machine Runbook — p5-m3

Operator-driven proof for Phase 5 / m3. Methodology: same-host marketplace install (see `creative-clean-machine-e2e.md`). **Do not treat local/dev loaders as the primary success path.**

## Known caveats (not in-scope for this build)

| Item | Status | Notes |
| --- | --- | --- |
| Cursor `sessionStart` dashboard hook | **Known fail** | Filed as [#12](https://github.com/Texarkanine/stockroom/issues/12) — WSL/minimal PATH; Claude `SessionStart` works. **Out of scope for m3 build** (operator: document only, do not fix here). Dashboard surface still proven via `stockroom dashboard` / `sr-dashboard`. |
| `STOCKROOM_HOME` isolation | **Skipped this run** | Operator completed `sr-initialize` against the default XDG home before the runbook was authored. Proof uses marketplace-sourced `engine-dir` + populated default warehouse (both harnesses present). |

## 0. Prerequisites (agent)

- [x] Packaging tests green (`make test` / pytest: 424 passed, 3 skipped)
- [x] Release lockstep `0.1.1` — tags `v0.1.0` / `v0.1.1`; PR #11 synced both plugin manifests + `.release-please-manifest.json` + CHANGELOG
- [x] Marketplace on `main` — stockroom in Cursor + Claude catalogs, no version pin (PR #2 merged)

## 1. Marketplace install (operator)

- [x] Add `https://github.com/Texarkanine/txrk9-agent-plugins` / `Texarkanine/txrk9-agent-plugins`
- [x] Install `stockroom` in **Cursor**
- [x] Install `stockroom` in **Claude Code**
- Evidence: `stockroom doctor probe` → `engine-dir: .../.cursor/plugins/cache/txrk9-agent-plugins/stockroom/333a8c7.../skills/sr-search`

## 2. Initialize (operator)

- [x] Cursor: `/sr-initialize` (or equivalent) completed — torch `2.13.0+cu126`, shim on PATH (`owner=cursor` per #12 report), schedule installed, warehouse populated
- [x] Claude: initialize / SessionStart path works (operator report; Claude hook launches dashboard)

## 3. Four surfaces (agent CLI verify)

Engine has no `search` subcommand — keyword/friendly search is the **`sr-search` skill** (routes to query/semantic). CLI proofs:

| Surface | How verified | Result |
| --- | --- | --- |
| Query | `stockroom query 'SELECT harness, count(*) …'` | `claude 39` / `cursor 806`; `messages` = 30603 |
| Semantic | `stockroom semantic 'marketplace install' --limit 2` | ranked hits, exit 0 |
| Dashboard | `stockroom dashboard` → `http://127.0.0.1:6767/` ; `curl` → 200 | pass |
| Search (skill) | Operator: `/sr-search` / `/stockroom:sr-search` | pass (operator) |

## 4. Skill invocation forms (operator)

Documented forms from README — mark when exercised post-marketplace install:

- [x] Cursor: `/sr-search`, `/sr-query`, `/sr-semantic`, `/sr-dashboard`
- [x] Claude: `/stockroom:sr-search`, `/stockroom:sr-query`, `/stockroom:sr-semantic`, `/stockroom:sr-dashboard`
- [x] Claude SessionStart auto-dashboard — works
- [ ] Cursor sessionStart auto-dashboard — **fails; see #12** (manual `/sr-dashboard` / CLI still OK)

## 5. Pass criteria for m3 bookkeeping

- Release-please exercised (lockstep manifests) — **met**
- Marketplace install both harnesses — **met**
- `sr-initialize` + warehouse with real Cursor **and** Claude history — **met**
- Four surfaces usable — **met** (CLI + skill slash-forms both harnesses)
- Cursor sessionStart hook — **known open bug #12**, not a Phase-5 gate for the four surfaces
