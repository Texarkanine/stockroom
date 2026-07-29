# Decision: PR Template Maturity

## Context

**What:** the content and shape of `.github/pull_request_template.md`, now that the ADHD-brevity constraint from #101 has been explicitly withdrawn by the operator ("We can be longer. We must not be inadequate.").

**Why it matters:** the template is the only lever that acts *before* review. Research across all 68 closed PRs (147 inline review comments, 92 conversation comments) plus warehouse history of PR-feedback sessions found that every P0/P1 finding this repo has ever received was an undisclosed divergence between what a PR claimed and what its diff did:

| PR | Severity | Finding |
|---|---|---|
| #44 | P0 | `Makefile` referenced `scripts/localdev.sh`, which the PR never added |
| #76 | P0 | A test asserted cookbook pages are symlinks; the PR shipped regular files |
| #70 | P1 | The creative doc said bucket by `messages.ts`; the code used session activity |
| #61 | P1 | Helper took `wait_free`; the test called `wait_port_free_fn` |
| #103 | P1 | The PR body listed `test_github_templates.py` as a deliverable; HEAD deleted it |

Roughly half of all CodeRabbit inline comments target stale prose (`memory-bank/active/*`, `CHANGELOG.md`, `docs/`) rather than code. Cross-platform nits recur and are routinely dismissed on scope grounds ("Window support is a future task, if ever. Use WSL." — #64). The maintainer's actual merge signal is manual verification ("works on my machine" / "LGOMM", sometimes with pasted query output on #85), which the shipped template does not collect.

**Constraints:**

- Must not restate `CONTRIBUTING.md`, and must keep linking to it visibly (a QA fix on #103).
- Must preserve release-consequence guidance: `feat`/`fix` release, `chore` must-not-release, squash title becomes the changelog entry.
- **Nothing that can be a hard CI check belongs in the template** (operator constraint, added during review of v1).
- Must be fillable by a human on a two-line fix and by an agent on a 40-file feature.
- Must survive force-pushes: the body is written early, and the defect is that nobody updates it.
- GitHub renders one template from this path; HTML comments are invisible in the merged body but present in the author's edit box.
- #103 deleted `test_github_templates.py` with `fix(docs): don't test prose`, so the template cannot lean on structural tests to stay honest.

## Options Evaluated

- **A — Evidence Ledger**: structured tables (claims, gates, platforms, contracts, prose) for maximum falsifiability and minimum prose.
- **B — Narrative with Teeth**: prose sections with a checklist rewritten so each item is checkable rather than merely affirmable.
- **C — Divergence-First Attestation**: organized around the gap between stated intent and shipped outcome, framed as an author attestation.
- **D — Unautomatable-Only** (selected; emerged from operator review of B): every section is something CI structurally cannot check, no checklist at all, mechanical gates moved into CI.

A structural alternative — splitting into `.github/PULL_REQUEST_TEMPLATE/` with multiple named templates — was considered and rejected: GitHub only offers those via a `?template=` query parameter, never in the default PR UI, so the directory would be invisible to exactly the authors it was meant to serve.

## Analysis

| Criterion | A — Ledger | B — Narrative + Teeth | C — Divergence-First | D — Unautomatable-Only |
|---|---|---|---|---|
| Attacks claim-vs-diff | Strong, per-claim | Moderate, via checklist | Strongest, names it | Strong, via Goal/What's-here seam |
| Duplicates CI gates | No | **Yes — 3 items** | **Yes — 3 items** | No, by construction |
| Stays true after force-push | Weak | Weak | Strong | Strong |
| Hand-fillable on a small PR | Poor | Good | Fair | Good |
| Cost when ignored | High — empty tables render as clutter | Low | Low | Low |
| Covers irreversible change | No | No | No | Yes |

Key insights:

- **A checkbox is a weaker form of a claim than a sentence is.** Ticking a box feels like discharging the obligation. #103 proves it: "Tests written before the fix/feature" was ticked in the very PR whose HEAD commit deleted the test file. Naming the test would have been self-refuting; ticking the box was frictionless. This kills the checklist as a device, not merely its redundant rows.
- **Verified CI coverage** (`ci.yml`, `docs.yaml`, both on `pull_request`): ruff check, ruff format, pytest, dashboard JS tests, lock-staleness, `reuse lint`, and `properdocs build --strict`. Conventional-commit PR title is **not** checked and no title/commit lint exists in any workflow — that is the one mechanical item still riding on author honor.
- **Self-report cannot catch unawareness.** A "contract impact" field would not have caught #70: the creative doc stated the grain rule, the code violated it, and the author would have written "none" sincerely. Such a field only catches authors who already know, who mostly get it right. Friction aimed at a population of zero.
- **The user-facing contract is wider than "UI."** Because `sr-query` invites users to write SQL directly against the warehouse, schema columns are a public interface alongside CLI flags, `--format`/`--detail` output shapes, dashboard views, env vars, and documented skill behavior. Asking "what changes for a user" captures all of it without asking authors to introspect about invariants.
- **Preemptive non-goals are a guess about what a reviewer will complain about** — low hit rate, permanent tax. The valuable case ("I deliberately dropped/deferred this") is a statement about what shipped and belongs there.
- **v1's divergence section only had content because another section was expected to be stale.** Designing a section whose value depends on another section rotting is indefensible; differentiate by source and tense instead (Goal = the ask, before; What's here = the branch, last).
- **Irreversibility was the real gap.** Every other axis describes a defect a follow-up PR can fix. Migrations are numbered and forward-only; once a user's warehouse is migrated it's migrated. Re-embeds can cost hours. `productContext.md` sells "Doesn't break your data" as a headline benefit, and neither CI nor the template asked about it — CI tests a fresh warehouse every time and never sees a user's.

## Decision

**Selected**: Option D — Unautomatable-Only. Five prose sections, no checklist, release guidance in a top-of-body HTML comment, and the one mechanical gate promoted into CI.

**Rationale**: The operator constraint ("don't put things in a checklist that can be a hard CI check") audits down to three of eight items being verbatim duplicates of existing gates, one belonging in CI, and the four survivors being claims that a checkbox actively launders. Deleting the checklist and adding a title check is therefore strictly stronger than hardening it. The remaining sections each answer a question CI structurally cannot: whether the diff matches the ask, whether anyone ran it on a surface CI can't reach, what a user will notice, and whether an existing warehouse is affected irreversibly.

**Tradeoff**: nothing in the body is machine-verifiable, so the template's force is entirely social — it makes claims cheap to falsify rather than impossible to fake. Per #103's `fix(docs): don't test prose` precedent, no structural tests should be added to compensate.

## Implementation Notes

- Rewrite `.github/pull_request_template.md` to the v2 draft below.
- **Add a conventional-commit PR title check** to CI on `pull_request`. This is what earns the right to delete the checklist; without it the title claim regresses to nothing.
- No new tests on the template. At most assert the file exists; do not re-add prose assertions deleted by #103.
- No `CONTRIBUTING.md` change needed — the template links to it and does not duplicate it.
- **Goal stays as its own section** (operator decision). It was weighed against collapsing into a single "What's here" that must describe HEAD, letting `closes #N` carry the ask; kept because several merged PRs (#46, #58, #62) carried no issue link at all, and those are precisely the ones where an unstated ask hurts.
- Follow-on, separate from this task: `memory-bank/active/*` staleness is the largest single review-comment category and no PR template can fix a workflow that writes plans early and reconciles them late.

### v2 draft (selected)

~~~markdown
<!-- Title: conventional commit. feat/fix cuts a release — changelog entry plus a docs-site
     publish; chore does not. Squash-merge uses the title as the changelog entry, so write it
     for someone reading CHANGELOG.md. Process details: CONTRIBUTING.md -->

Process details: [CONTRIBUTING.md](../CONTRIBUTING.md)

## Goal

<!-- What this needs to accomplish, in a line. If there's an issue, "closes #N" plus a clause
     is plenty — the issue is already the goal statement. -->

## What's here

<!-- Write this last, against the branch as it stands — not the plan you opened with.
     If it ended up somewhere other than the Goal (scope added or dropped, an approach
     abandoned, something deferred to a follow-up), that sentence is the most useful one in
     this PR. Every P0/P1 this repo has received was an undisclosed gap between these two. -->

## How I know it works

<!-- Name the tests that cover this, and paste the run that convinced you. CI cannot exercise
     torch, launchd, WSL mounts, the dashboard UI, or macOS — if this touches any of those,
     this section is the only evidence that exists. -->

**Tests:**

**Exercised on:** <!-- Linux/WSL · macOS · neither. "Neither" is a fine answer; unstated is not. -->

<details>
<summary>Transcript</summary>

```

```

</details>

## What changes for a user

<!-- Anything a user can notice or depend on: CLI flags and output shapes, skill behavior,
     warehouse columns (sr-query users write SQL against them), dashboard views, env vars,
     setup steps. "Nothing user-visible" is a common and useful answer. If something did
     change, docs/ should say so — the strict docs build won't catch prose that's merely false. -->

## Effect on an existing warehouse

<!-- Migration, re-embed, re-ingest, or none. This is the one axis a follow-up PR can't undo:
     migrations are forward-only, and a re-embed can cost someone hours. Usually "none". -->
~~~

### Superseded v1 draft

Retained because the reasoning that killed it is the most transferable finding here: it duplicated three CI gates in a checklist, asked authors to self-report contract impact they demonstrably cannot know, invited speculative non-goals, and made its divergence section depend on another section going stale.

~~~markdown
Process details: [CONTRIBUTING.md](../CONTRIBUTING.md)

## What & why

<!-- 1–3 sentences. Link issues with #N. -->

## What actually shipped

<!-- Where the final commit differs from the intent above. -->

## How I know it works

**Tests:**

**Exercised on:**

## Contracts and prose

- **Contract impact:**
- **Text this invalidated:**

## Not in this PR

## Checklist

- [ ] Title is a conventional commit …
- [ ] Tests were written first, and they failed first
- [ ] Every file, test, and behavior named above exists in the final commit
- [ ] "What actually shipped" is current as of the final push
- [ ] `make ci` passes
- [ ] `make docs-build` passes
- [ ] `make reuse` passes
- [ ] Change stays in its stated scope
~~~
