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
