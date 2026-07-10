# Task: end-of-roadmap docs cutover

* Task ID: end-of-roadmap-docs-cutover
* Complexity: Level 2
* Type: simple enhancement (documentation cutover)

Re-initialize persistent memory-bank files from current stockroom reality, stash user-facing docs in a plain `docs/` directory (no doc site / no docs CI), trim the README to slobac level (present-tense only), scrub remaining `planning/` references in kept files, and delete `planning/`.

## Test Plan (TDD)

Documentation cutover — no product code behavior. Verification is assertion-style checks run during build (shell/`rg`), not a new pytest suite or docs CI. Operator clarified: `docs/` is a markdown stash only; no doc-site tooling.

### Behaviors to Verify

- [B1 persistent MB self-contained]: after rewrite, `rg 'planning/' memory-bank/productContext.md memory-bank/systemPatterns.md memory-bank/techContext.md` → no matches
- [B2 no hard wraps in persistent MB]: each prose paragraph in the three persistent files is a single line (no mid-paragraph newlines); headings/lists/code fences unchanged
- [B3 present-tense MB]: persistent files describe how stockroom is — no roadmap/phase-build narrative, no "until the cut" / "accrete from planning" framing, no future-commitment sections
- [B4 docs stash exists]: `docs/` contains markdown covering user-facing material moved out of the oversized README (install/usage and contributor/dev guidance as separate files or clearly sectioned)
- [B5 no docs site/CI]: no `mkdocs.yml` / `properdocs.yaml` / docs workflow added; `docs/` is plain markdown
- [B6 README slobac-level]: README is short, present-tense product orientation with links into `docs/` where detail lives; no origin story, roadmap, or "what might be planned"; roughly comparable to `../slobac/README.md` scale
- [B7 no planning refs in kept docs]: `rg 'planning/' README.md docs/` → no matches
- [B8 code comment scrub]: `rg 'planning/' skills/sr-search/pyproject.toml skills/sr-search/src/stockroom/__main__.py skills/sr-search/src/stockroom/ingest/paths.py` → no matches (rephrase comments to point at code/contracts, not deleted spikes)
- [B9 planning deleted]: `test ! -e planning` (directory gone)
- [B10 no broken kept pointers]: memory-bank persistent files, README, and `docs/` do not link to paths under `planning/`
- [Edge: agent-facing vs user-facing]: `skills/sr-search/references/system-model.md` stays put (agent/system model, not user docs); do not duplicate it into `docs/`
- [Edge: archives]: `memory-bank/archive/**` may retain historical `planning/` mentions; out of scope to rewrite (cut gate is active persistent files + user docs)

### Test Infrastructure

- Framework: none for docs (no existing README/docs test suite; operator forbids docs CI/site for now)
- Verification location: build-phase shell checks against the behaviors above
- Conventions: N/A — do not introduce parallel test infrastructure
- New test files: none

## Implementation Plan

1. **Inventory & content map (no file writes yet beyond this plan)**
   - Files: `README.md`, `planning/product-brief.md`, current persistent MB files, `skills/sr-search/references/system-model.md`
   - Changes: decide README keep vs `docs/` move. Planned split:
     - `README.md` — what stockroom is; marketplace install (short); first-time `sr-initialize` pointer; skills table or link; license; link to `docs/` for detail
     - `docs/using.md` (or similar) — fuller install (marketplace + local/dev load), first-time setup, skills/invocation, post-setup usage, known caveat (#12)
     - `docs/development.md` — Makefile targets, torch-safe run contract, shim/`stockroom` ad-hoc invocation, bootstrap footnote
   - Discard with `planning/` (do not move to `docs/`): roadmap, briefs-as-history, brainstorm, spikes

2. **Rewrite `memory-bank/productContext.md`**
   - Files: `memory-bank/productContext.md`
   - Changes: full re-init from current product reality (distill present-tense audience/use cases/benefits/success/constraints from the brief + shipped skills). No `planning/` pointers, no hard wraps, no origin-story problem essay, no future non-goals list framed as roadmap

3. **Rewrite `memory-bank/systemPatterns.md`**
   - Files: `memory-bank/systemPatterns.md`
   - Changes: present-tense "how this system works" + load-bearing patterns pointing at code (`skills/sr-search/…`, hooks, Makefile). Remove planning/spike/brainstorm links and "Phase N / until archived creative" temporal scaffolding where it reads as build history. Soft-wrap prose. Keep patterns that still hold (torch-out-of-lock, no truncation at rest, harness-labeled schema, shim owns invocation, warehouse chokepoint, etc.)

4. **Rewrite `memory-bank/techContext.md`**
   - Files: `memory-bank/techContext.md`
   - Changes: stand-alone tech orientation pointing at canonical artifacts (`pyproject.toml`, `uv.lock`, migrations, Makefile, CI). Remove all `planning/` links. Design system section points at shipped dashboard static assets / code, not brainstorm HTML. Soft-wrap prose. Trim phase-milestone narrative; keep "where things live" pointers

5. **Create `docs/` and move user-facing detail**
   - Files: `docs/using.md`, `docs/development.md` (names may adjust slightly; keep few files)
   - Changes: plain markdown stash only — no site generator, no CI. Content present-tense. Link from README

6. **Trim `README.md`**
   - Files: `README.md`
   - Changes: slobac-comparable length/tone; present-tense only; point to `docs/` for depth; drop planning/spike links and build-history framing

7. **Scrub code comments that cite `planning/`**
   - Files: `skills/sr-search/pyproject.toml`, `skills/sr-search/src/stockroom/__main__.py`, `skills/sr-search/src/stockroom/ingest/paths.py`
   - Changes: rephrase comments to describe the contract/fact without pointing at deleted spikes (e.g. torch override rationale stays; path drops `planning/spikes/…`)

8. **Delete `planning/`**
   - Files: entire `planning/` tree
   - Changes: `git rm -r planning/` (or equivalent) after steps 2–7 land

9. **Verify behaviors B1–B10**
   - Files: N/A (shell checks)
   - Changes: run the verification commands; fix any remaining refs before declaring build done

## Technology Validation

No new technology - validation not required. `docs/` is a plain directory of markdown; no doc-site generator, no docs CI/CD.

## Dependencies

- Current persistent MB + product brief (as source material to distill, then discard with `planning/`)
- `../slobac/README.md` as length/tone reference
- Operator constraint: `docs/` stash only (no site/CI now)

## Challenges & Mitigations

- **What belongs in `docs/` vs README vs memory-bank:** Mitigate with the split above — user install/usage → `docs/`; contributor torch/Makefile → `docs/development.md`; agent architecture → persistent MB + existing `system-model.md`; pitch → README
- **Over-preserving planning history:** Mitigate by clean-break — spikes/brainstorm/roadmap are deleted, not relocated
- **Hard-wrap regression while editing long MB files:** Mitigate by writing each prose paragraph as one line; avoid editor auto-wrap
- **Stale `planning/` refs in code comments / archives:** Scrub the three known code hits; leave `memory-bank/archive/**` historical text alone unless a kept active file links to it
- **TDD without docs tests:** Mitigate with explicit shell verification behaviors (B1–B10); do not add docs CI

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
