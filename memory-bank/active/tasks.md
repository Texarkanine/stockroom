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

Content map (fixed by plan; not a build step):
- `README.md` — what stockroom is; short marketplace install; `sr-initialize` pointer; skills overview or link; license; links into `docs/`
- `docs/using.md` — fuller install (marketplace + local/dev), first-time setup, skills/invocation, post-setup usage, caveat (#12)
- `docs/development.md` — Makefile, torch-safe run contract, shim/`stockroom` invocation, bootstrap footnote
- Discard with `planning/` (do not relocate): roadmap, briefs-as-history, brainstorm, spikes
- Keep in place: `skills/sr-search/references/system-model.md` (agent-facing)

1. **Establish failing verification (TDD red)**
   - Files: none yet (shell only)
   - Changes: run the B1–B10 check commands against the current tree; confirm they fail for the expected reasons (planning refs present, no `docs/`, README oversized, `planning/` exists). This is the red baseline before any rewrite.

2. **Rewrite `memory-bank/productContext.md` → re-check B1–B3 for this file**
   - Files: `memory-bank/productContext.md`
   - Changes: full re-init from current product reality (present-tense audience/use cases/benefits/success/constraints). No `planning/` pointers, no hard wraps, no origin-story essay, no future-roadmap framing.
   - Verify: `rg 'planning/' memory-bank/productContext.md` empty; prose paragraphs are single lines.

3. **Rewrite `memory-bank/systemPatterns.md` → re-check B1–B3 for this file**
   - Files: `memory-bank/systemPatterns.md`
   - Changes: present-tense how-it-works + load-bearing patterns pointing at code. Remove planning/spike/brainstorm links and build-history scaffolding. Soft-wrap prose. Keep patterns that still hold.
   - Verify: no `planning/` matches; no hard wraps in prose.

4. **Rewrite `memory-bank/techContext.md` → re-check B1–B3 for this file**
   - Files: `memory-bank/techContext.md`
   - Changes: stand-alone tech orientation pointing at canonical artifacts. Design system → shipped dashboard static assets. Soft-wrap prose. Trim phase-milestone narrative.
   - Verify: no `planning/` matches; no hard wraps in prose.

5. **Create `docs/` stash → re-check B4–B5**
   - Files: `docs/using.md`, `docs/development.md`
   - Changes: plain markdown only (no site generator, no CI). Present-tense user/contributor detail moved out of README.
   - Verify: both files exist; no `mkdocs.yml` / `properdocs.yaml` / docs workflow added.

6. **Trim `README.md` → re-check B6–B7**
   - Files: `README.md`
   - Changes: slobac-comparable length/tone; present-tense; links to `docs/`; drop planning/spike links and build-history framing.
   - Verify: `rg 'planning/' README.md docs/` empty; README roughly slobac-scale.

7. **Scrub code comments that cite `planning/` → re-check B8**
   - Files: `skills/sr-search/pyproject.toml`, `skills/sr-search/src/stockroom/__main__.py`, `skills/sr-search/src/stockroom/ingest/paths.py`
   - Changes: rephrase comments to state the contract/fact without pointing at deleted spikes (behavior unchanged).
   - Verify: `rg 'planning/'` on those three paths empty.

8. **Delete `planning/` → re-check B9–B10**
   - Files: entire `planning/` tree
   - Changes: `git rm -r planning/` after steps 2–7 are green on their local checks.
   - Verify: `test ! -e planning`; kept docs have no `planning/` links.

9. **Full green gate**
   - Files: N/A
   - Changes: re-run the full B1–B10 suite; fix any remaining misses before declaring build done.

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
- [x] Preflight
- [x] Build
- [ ] QA

## Preflight Amendments

- Restructured Implementation Plan so each unit is test-before-code: step 1 establishes the failing B1–B10 baseline; steps 2–8 each rewrite then re-check their local behaviors; step 9 is the full green gate.
- Operator constraint reaffirmed: `docs/` is a markdown stash only (no site/CI).
