# Task: ADHD reorder of ingest / backfill user-guide pages

* Task ID: cursor-vscdb-backfill-adhd-docs
* Complexity: Level 2
* Type: simple enhancement (docs)

PR-feedback rework: reorder and cut `docs/user-guide/ingest/{index.md,backfill/index.md,backfill/cursor-vscdb.md}` for ADHD scan/action fit; fix link fallout from nesting backfill under `ingest/`. No engine or CLI changes.

## Test Plan (TDD)

Docs-only work: no pytest behaviors. Verification is the strict docs build (link + structure) plus a small path-presence checklist exercised before/after edits.

### Behaviors to Verify

- B1: First viewport of `ingest/index.md` shows the incremental catch-up commands before ETL mental-model prose.
- B2: `ingest/index.md` has a one-line door to `backfill/index.md` for legacy history.
- B3: `backfill/index.md` opens with one-sentence what-it-is then the Required Sequence; sequence is quit → ingest → backfill → embed (four steps).
- B4: `backfill/index.md` has no "Why is This Even a Problem?" section; Why Quit / Why Ingest First are each ≤ one sentence (or one short para each, not multi-bullet essays).
- B5: `backfill/index.md` Running It leads with bare `stockroom backfill`.
- B6: `cursor-vscdb.md` Pointing At The Store recommends config first, then flag/env.
- B7: `cursor-vscdb.md` How It Reads states the silent-miss consequence of leaving Cursor open; no HTML-commented TODO block remains.
- B8: `cursor-vscdb.md` `models` cell is softened; Model Attribution + Token Counts live under one Reference heading.
- B9: No remaining links to `user-guide/backfill/` (without `ingest/`); no `../ingest.md` or `ingest.md` targets that miss the directory index; `make docs-build --strict` exits 0.

### Edge Cases

- Architecture anchors `#the-required-sequence` / `#how-it-reads` still resolve after heading edits.
- Troubleshooting pointers at `../ingest.md` / `#scheduling` still resolve after the nest.
- Relative links from `ingest/index.md` to sibling user-guide pages use `../` (broken since the file moved into `ingest/`).

### Test Infrastructure

- Framework: ProperDocs / MkDocs strict build (`make docs-build` with `--strict`)
- Test location: n/a (no pytest); verification command from repo root
- Conventions: human docs under `docs/`; agents do not consume them (`systemPatterns.md` Docs ownership)
- New test files: none

## Implementation Plan

1. **Link hygiene first (fail the strict build on purpose if needed, then fix)**
   - Files: `docs/architecture/backfill.md`, `docs/contributing/backfill-adapters.md`, `docs/user-guide/troubleshooting/index.md`, and any `../ingest.md` / `user-guide/backfill/` hits under `docs/`
   - Changes: retarget to `user-guide/ingest/backfill/…` and `../ingest/` (or `../ingest/index.md`); fix `ingest/index.md` outbound links to `../quickstart.md`, `../installed-layout.md`, `../troubleshooting/…`
   - Verify: `rg 'user-guide/backfill[^/]|ingest\.md' docs/` clean of stale targets; `make docs-build --strict`

2. **Rewrite `docs/user-guide/ingest/index.md` (ADHD flip)**
   - Files: `docs/user-guide/ingest/index.md`
   - Changes: open with one-sentence purpose + catch-up command block; then Embed / Scheduling as short sections; mental-model / ETL / chats best-effort below or as bullets; demote Cursor `sessions.models` Enrichment below Scheduling (or after the main flow); add **Legacy history?** → [Backfill](backfill/) link near the top catch-up block
   - Verify: B1, B2 by reading first ~25 lines

3. **Rewrite `docs/user-guide/ingest/backfill/index.md` (lede = Required Sequence)**
   - Files: `docs/user-guide/ingest/backfill/index.md`
   - Changes: one-sentence intro; Required Sequence as four steps (quit, ingest, backfill, embed); one-sentence Why Quit + one-sentence Why Ingest First; delete "Why is This Even a Problem?"; Running It leads with `stockroom backfill` then dry-run/verbose; keep Fixing / Undoing / Where Next; fix `../ingest.md` → `../index.md#ingest` (or `../#ingest`)
   - Verify: B3–B5; architecture link to `#the-required-sequence` still valid

4. **Rewrite `docs/user-guide/ingest/backfill/cursor-vscdb.md` (config-first + silent-miss)**
   - Files: `docs/user-guide/ingest/backfill/cursor-vscdb.md`
   - Changes: Pointing At The Store leads with config TOML + "recommended for re-runs", then flag/env; How It Reads: bold silent-miss line + ≤2 short sentences, delete HTML TODO comment; soften `models` cell; fold Model Attribution + Token Counts under `## Reference`; fix ingest/dashboard relative links
   - Verify: B6–B8; `#how-it-reads` still exists for architecture pointer

5. **Strict docs build + final scan**
   - Run `make docs-build --strict`
   - Confirm B9; no leftover HTML comments in the three pages

## Technology Validation

No new technology - validation not required.

## Dependencies

- Existing ProperDocs toolchain (`make docs-build`)
- Content already accepted in Reflect; this rework is presentation + link correctness only

## Challenges & Mitigations

- **Over-cutting Why sections loses the quit↔ingest interaction insight:** Keep one sentence each that names the cost (silent miss / wasted embed), not the mechanism essay.
- **Heading renames break architecture anchors:** Keep heading text `The Required Sequence` and `How It Reads` literally.
- **ingest/index.md sibling links already broken from the nest:** Step 1 fixes them before ADHD rewrite so the strict build is a real gate, not a surprise at the end.

## Pre-Mortem

- **We "ADHD-ified" by deleting required safety content:** Plan response — Required Sequence stays a warning admonition with four numbered steps; only the tangent "Why is This Even a Problem?" is deleted.
- **Strict build still fails on an unlisted pointer (e.g. lifecycle, iteration):** Plan response — Step 1 is a full `docs/` ripgrep for stale `user-guide/backfill` and `ingest.md` targets, not only the files named in the brief.
- **We rewrite tone so hard the pages diverge from architecture:** already covered by Challenge 1 (keep consequence sentences; leave ladder on architecture).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
