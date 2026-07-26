---
task_id: cursor-vscdb-backfill
date: 2026-07-26
complexity_level: 3
---

# Reflection: Cursor state.vscdb one-shot backfill

## Summary

Shipped `stockroom backfill` — a harness-neutral one-shot orchestrator with a `cursor_vscdb` adapter — and the operator's live warehouse is correctly backfilled (610 sessions / ~64k messages). The nine planned TDD steps landed clean; the substantive gaps (model attribution, failed-call husks, dry-run locking) were found only after the first real run and docs pass, not by QA on the planned code.

## Requirements vs Outcome

Every acceptance criterion in the project brief held: read-only vscdb excavation, tokens not a selection gate, message-grain token attribution, provenance via `source_path`, opt-in CLI with a documented adapter contract, nightly path untouched, suite green. Operator hand-verified the warehouse.

**Additions beyond the plan** (all justified, all TDD'd):

| Addition | Origin |
|---|---|
| Model attribution (`sessions.models` / `messages.model`) | Planning omission — columns never named, so no test could fail |
| Decline blank-name tool husks | Live-store probe after dashboard showed a 21% unnamed Top Tools slice |
| `--dry-run` via `warehouse.open_current()` | Docs pass exposed that dry-run took the writer lock and could create a warehouse |
| Docs restructured into `user-guide/backfill/`, `architecture/backfill.md`, `contributing/backfill-adapters.md` | Operator feedback |
| Required operating sequence (quit → ingest → backfill) as REQUIRED, not advisory | Operator feedback + the silent-cost analysis writing it forced |
| Dashboard `All` date range + Top Models clamp to 10 | Adjacent side requests on the same branch while `--force` re-ran |

Nothing in the brief was dropped. The deliberate #84 deviation (tokens not a gate) stayed.

## Plan Accuracy

The plan's sequence, file list, and nine TDD steps were accurate. Preflight amended six places before build (explicit TDD substeps, abort-era config ratchet named for deletion, `__main__.py` placement, `cli.md` dropped, D7 `--force`, D8 `source_mtime`/`first_seen_at` decoupling) — all of those amendments held, and D8 stayed the promised one-liner with pre-existing tests untouched.

What the plan got wrong was not *steps* but *completeness of the column inventory*. It enumerated every `NormalizedSession` / `NormalizedMessage` field that mattered for structure, tokens, and identity — and never asked about `models` / `model`, even though the live store carries both grains. Challenges that *were* predicted (WAL on the mount, multi-GB I/O, embed backlog, no discoverable default path) all behaved as expected. Surprises came from shapes the synthetic fixtures never produced: `modelConfig` / `modelInfo`, and husk `toolFormerData` with only `additionalData.status == "error"`.

D3 and D6 revisions during operator plan review were load-bearing: the original Cursor-hardcoded surface and session-Σ tokens were cargo-culted from the aborted `enhance-cursor-tokens` enrich design. Carrying a decision across a change of mechanism silently carried its constraint.

## Creative Phase Review

**OQ1 — storable-bubbles-only (Option B)** held. Tool calls stayed on their own bubble-messages; thinking-only and empty bubbles dropped; per-bubble timestamps and tokens stayed aligned. The husk fix refined the keep predicate without overturning it: "`toolFormerData` present" became "`toolFormerData` with a non-blank name" — the creative's intent (store only what the schema can attribute) applied one step further. Declining husks also dropped ~5,392 empty messages the husk alone had been making storable, which is exactly what the keep predicate exists to exclude.

**OQ2 — native `workspaceId` + `workspace.json` cwd (Option D)** held. Real-run coverage (377/610 `project_id`, 317/610 `cwd`) sat near the source's own ceiling; the bubble-level `workspaceUris` fallback was correctly declined as multi-root-ambiguous. Writer-derived `workspace_key` convergence with same-`cwd` transcript sessions was verified in integration tests and needed no rework.

Neither creative decision created QA findings. The friction that *did* appear — embedding invalidation when the keep set shrinks — is a consequence of `message_id = '{session_id}#{ordinal}'`, not of the creative choice itself. A column-fill fix (models) costs nothing to re-run; a keep-predicate change renumbers ordinals and drops vectors.

## Build & QA Observations

**Build of the nine planned steps was smooth.** Ordered TDD cycles held; the D8 inertness claim survived; guards pinned the nightly-path isolation. Two build-time corrections were worth keeping: the import-edge guard matches `stockroom.backfill` (not the bare word — a docstring that *explains* the protected case must be allowed to name it), and the pre-mortem's "one-line reversal" is actually three deletes through a DuckDB client because `stockroom query` is read-only and the schema has no FKs.

**QA found zero substantive issues.** Seven trivial findings, all in post-build / side-request code — docstring whitespace, a dead template literal, an unused aggregate property, and two documentation enumerations that stopped being exhaustive. The nine planned steps came through clean. That split is the story: preflight + TDD protected the planned surface; the addenda had real bugs to chase and no preflight in front of them.

**What actually found the substantive gaps** was the operator running the documented sequence against the live 5.7 GB store and reading the dashboard. Synthetic fixtures never emitted `modelConfig`, never emitted husk `toolFormerData`, and never contended the writer lock the way a 25-minute real run does.

## Cross-Phase Analysis

1. **Plan column inventory → post-build model gap.** The plan was thorough about every field it named and silent about the ones it didn't. TDD cannot fail a test that was never written; the gap was undetectable until the warehouse was full and the chart looked wrong. Same failure mode as QA's doc findings: enumerations that claim completeness go stale the moment something is added elsewhere (`techContext` engine-surfaces table, `SourceSummary` docstring fields, plan's session/message columns).

2. **Aborted-task residue → plan review saved D3/D6.** The negative ratchet `test_settings_has_no_state_vscdb_field` and the session-Σ token design both came from `enhance-cursor-tokens`. Preflight named the ratchet for deliberate deletion; operator review caught the cargo-culted Σ. Without that review, migration `0007` would have been violated by construction.

3. **Preflight caught the expensive mistake (D8).** The first preflight answer — use the vscdb file mtime — would have parked timeless composers on the run date in the dashboard's `COALESCE(started_at, source_mtime)` window. Operator pushback separated activity time from observation time. That is exactly the class of bug preflight exists to catch: cheap in plan, expensive once written into 60k rows.

4. **Docs pass → dry-run correctness.** Writing "dry-run does not open for writing" forced someone to check; it did. The fix reused `open_current()` rather than inventing a third open path. Prose as a verification surface, not just a deliverable.

5. **Creative keep predicate → husk refinement → embed cost.** OQ1's "toolFormerData present" was right for the shapes fixtures covered. The live store's error husks satisfied that predicate while carrying no attributable call. Fixing it shifts ordinals; the docs then owed an embed obligation that the memory bank knew a day before the user guide did.

6. **Side requests rode the branch cleanly** because they were dashboard-only and TDD'd, but they diluted QA's focus — every QA finding that wasn't a backfill docstring lived in that adjacent code. Acceptable for this run; worth noticing when a branch accumulates "while we wait" work.

## Insights

### Technical

- **Probe the live store before trusting the adapter's view of it.** Both substantive post-build bugs (models at 0/610, 17k blank tool names) were invisible from warehouse-only or fixture-only inspection. Asking `state.vscdb` what keys it actually carries — not what the parser reads — is the check that caught them.
- **`message_id = '{session_id}#{ordinal}'` makes keep-predicate changes expensive and column fills cheap.** Model attribution invalidated zero embeddings; declining husks invalidated ~15% of message vectors. Any future adapter change should ask which kind it is before recommending `--force`.
- **A column whose meaning is defined against one source shape does not survive a change of shape.** `source_mtime` answered both "activity time" and "observation-time seed" only while every parser had one file per conversation. The shared 5.7 GB store was the first source where those jobs diverge — and copying the *mechanism* (stat the source) instead of the *meaning* would have fabricated timeline positions.
- **`or ""` against a `NOT NULL` column is how blank identities get stored.** Declining the row was always available; the schema made the lossy choice feel required. When identity is the point of a column (`tool_name`, `model`), absent means decline, not empty string.
- **Closing the harness and ingesting first are not independent advice.** An immutable open cannot see the WAL tail; quitting checkpoints it and widens the ingest-overlap window that "ingest first" exists to close. Following one makes the other more necessary — which is why the docs elevated both from advisory to REQUIRED ORDER.

### Process

- **Enumerations that claim completeness are a recurring failure mode across plan, docs, and memory bank.** Plan missed `models`; user guide missed the `--force`→embed consequence; `techContext` missed the new surface. When a document lists "all of X," the next addition elsewhere is a latent bug. Prefer "see Y" indirection, or accept that exhaustive lists need an explicit update step in the plan.
- **Operator plan review of decisions inherited from aborted work is not optional ceremony.** D3 and D6 were wrong for reasons that only became visible when the mechanism changed; the abort archive explained the *old* constraint, and it was easy to carry forward. Flag "inherited from &lt;aborted task&gt;" decisions for explicit re-validation.
- **A real run against production data is the only test that can catch unnamed columns.** Keep it in the Level 3 loop when the source is an undocumented store — synthetic fixtures encode what the planner already knew. Budget for a dry-run-then-real-run between Build and QA, not only after.
- **Post-build addenda need the same discipline as planned steps, or QA will only find trivia in them.** Every QA finding lived in code written after the plan was validated. Test-first caught behavior; nothing watched prose and whitespace. When an addendum lands, a mini-preflight (or at least a doc/enumeration pass) pays for itself.
