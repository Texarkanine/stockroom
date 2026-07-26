# Task: Architecture atlas tighten for backfill.md

* Task ID: cursor-vscdb-backfill-arch-docs
* Complexity: Level 2
* Type: simple enhancement (docs)

PR-feedback rework: name fences up front on `docs/architecture/backfill.md`, cut design-diary voice in two paragraphs, and record the keep-predicate → `message_id` → embed invalidation trap. No engine or CLI changes. Prior ADHD user-guide pages stay as shipped.

## Test Plan (TDD)

Docs-only work: no pytest behaviors. Verification is the strict docs build plus a content checklist exercised before/after edits.

### Behaviors to Verify

- B1: Immediately under the page lede (before the first `##` section body / before or as first `##`), an **Invariants** heading lists four fences: never on nightly; writer-only / no watermark; skip set + `--force` provenance; token grain + `source_mtime` NULL for a shared store.
- B2: **Reuses The Writer** skip-set / ingest-first paragraph is materially shorter (~half) and still states: cost not correctness, nothing lost, embeds paid twice / summary corrupted, ingest first.
- B3: **Grain And Honesty** `source_mtime` / `first_seen_at` prose leads with what-is (`NULL` + run-clock fallback) then fence why; materially shorter; no “quieter job / latent gap” diary voice.
- B4: **Never Clobbering** / `--force` names that keep-predicate changes renumber `message_id`s and invalidate embeddings; does not paste the user-guide procedure.
- B5: Diagram, Not On Any Automatic Path, Orchestrator Over Adapters, and Reading Foreign Stores outbound pointer remain; `make docs-build --strict` exits 0.

### Edge Cases

- Heading anchors linked from elsewhere (`#the-required-sequence` lives on user-guide; architecture anchors if any) must not break.
- Invariants must not duplicate the full essays — punch list + essays, not punch list replacing essays.
- User-guide pages from the prior rework must not be edited in this task.

### Test Infrastructure

- Framework: ProperDocs / MkDocs strict build (`make docs-build` with `--strict`)
- Test location: n/a (no pytest); verification command from repo root
- Conventions: human docs under `docs/`; agents do not consume them (`systemPatterns.md` Docs ownership); Architecture is Diátaxis explanation (architecture-docs skill)
- New test files: none

## Implementation Plan

1. **Docs TDD baseline (fail first) + Invariants block**
   - Files: `docs/architecture/backfill.md`
   - Changes:
     1. **Fail first:** read the page and confirm B1–B4 currently fail (no Invariants heading; skip-set and `source_mtime` paragraphs are the long diary forms; no keep-predicate / embed sentence under `--force`).
     2. After the lede paragraph(s) and before `## Not On Any Automatic Path`, insert `## Invariants` with a four-bullet punch list of the load-bearing fences. Keep each bullet one line.
   - Verify: B1 by reading the first ~25 lines

2. **Tighten Reuses The Writer (skip-set / cost)**
   - Files: `docs/architecture/backfill.md`
   - Changes: Rewrite the paragraph that explains why the required operating sequence is cost rather than correctness — lead with what (skip set = warehouse snapshot), then fence why (overlap paid twice in embeds; summary corrupted; nothing lost because watermark untouched). Target ~half length. Keep the dry-run / `open_current` paragraph unless it is already tight.
   - Verify: B2 (re-read the tightened paragraph against the checklist)

3. **Add keep-predicate / embed fence under Never Clobbering**
   - Files: `docs/architecture/backfill.md`
   - Changes: After the `--force` paragraph, add one sentence: changing the keep predicate under `--force` renumbers `message_id`s and invalidates embeddings. Link to [User Guide → Fixing A Run](../user-guide/ingest/backfill/index.md#fixing-a-run); do not paste commands.
   - Verify: B4

4. **Tighten Grain And Honesty (`source_mtime` / `first_seen_at`)**
   - Files: `docs/architecture/backfill.md`
   - Changes: Rewrite the `source_mtime` + `first_seen_at` paragraphs to lead with what-is then fence why; drop design-diary voice. Keep the tokens-at-source-grain paragraph (already tight).
   - Verify: B3

5. **Final scan + strict docs build**
   - Files: `docs/architecture/backfill.md` (read-only check)
   - Changes: Confirm B1–B5; `make docs-build --strict` green
   - Verify: B5

## Preflight Amendments (2026-07-26)

- Encoded docs TDD order in Step 1: confirm B1–B4 fail on the live page before any edit.
- Pin the `--force` outbound link to `#fixing-a-run` on the user-guide backfill index.

## Technology Validation

No new technology - validation not required.

## Dependencies

- Existing ProperDocs toolchain (`make docs-build`)
- Content already accepted in prior reflect; this rework is presentation + one missing fence name only
- architecture-docs skill inclusion bar (do not cut mechanism the user-guide left on architecture)

## Challenges & Mitigations

- **Invariants become a second copy of every section:** Keep bullets to fence names only; essays stay the explanation. If a bullet needs more than one line, cut the essay not the bullet.
- **Over-cutting loses the quit↔ingest interaction insight:** Keep “nothing lost / embeds paid twice / summary corrupted” in the tightened paragraph; do not delete the fence.
- **Pasting the `--force` embed recipe into Architecture:** One sentence + outbound link only; procedure stays on the user guide.

## Pre-Mortem

- **We ADHD-cut so hard the page stops being an atlas:** Plan response — B5 explicitly preserves diagram and structural sections; inclusion bar is “name fences + tighten diary,” not “match user-guide brevity.”
- **Invariants list drifts from essay content:** Plan response — draft the four bullets from the existing section titles/claims already on the page, then tighten essays without changing claims.
- **Strict build fails on an unrelated nest link:** Plan response — prior rework already greened the tree; this task touches one file. If strict fails, fix only regressions caused by this edit unless a one-line path fix is obvious and in-scope.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight (PASS with amendments)
- [x] Build
- [ ] QA

## Build checklist

- [x] Step 1 — Invariants block
- [x] Step 2 — Tighten Reuses The Writer
- [x] Step 3 — keep-predicate / embed fence
- [x] Step 4 — Tighten Grain And Honesty
- [x] Step 5 — final scan + `make docs-build` (strict)
