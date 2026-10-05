# Project Brief

## User Story

As someone searching captured agent history by meaning, I want `stockroom semantic` to optionally limit ranking to one harness and/or one speaker role, so that I can ask where I talked, where the assistant talked, or where we talked in a known harness.

## Use-Case(s)

### Use-Case 1

Unfiltered meaning search stays as it is. `stockroom semantic "where we talked about flock"` ranks the whole corpus.

### Use-Case 2

A speaker scope. `--role user` is where I talked. `--role assistant` is where you talked.

### Use-Case 3

A harness scope, alone or with a role. `stockroom semantic --harness claude --role user "where I talked about flock in Claude"` ranks only that intersection.

## Requirements

1. `stockroom semantic` accepts optional `--harness` and `--role`. Omitting a flag leaves that dimension open. The two flags combine with AND.
2. `--role` accepts only `user` and `assistant`. Any other value is a bad request and exits 2.
3. `--harness` is one free exact string. The set stays open for later harnesses. An unknown value is an empty result and exits 0.
4. Each flag takes one value. Repeating a flag is not OR.
5. A scope changes which messages are nearest. It is applied before the result list is cut to `-k`. It is not a filter over an already chosen top `-k`, and it is not a `WHERE` on the current HNSW `ORDER BY distance LIMIT` query.
6. When neither flag is set, ranking stays the current HNSW path. When either is set, rank `embeddings` joined to `messages` under those equalities, then the existing max-sim dedup and cut to `-k`.
7. A nearer out-of-scope neighbor must not hide an in-scope neighbor.
8. `sr-semantic` teaches the pronoun map and stops saying that every filter belongs to `sr-query`. Meaning plus these two scopes is semantic. Ids, counts, dates, and projects stay `sr-query`. An empty scoped result means nothing in that scope matched.
9. `sr-search` may pass these flags when the question names a speaker or a harness.

## Constraints

1. The decision in `memory-bank/active/creative/creative-semantic-cli-filters.md` is the design. Do not reopen it.
2. No project, cwd, workspace, model, time, or entrypoint filters. No skipping ordinal 0. No boilerplate suppression.
3. No new vector extension and no per-harness indexes.
4. Read-only search. Existing `--format`, `--detail`, and `-k` behavior stays.
5. A pending major version bump on main is orthogonal to this work.
6. Carry the work through reflect, then open a non-draft pull request and leave it waiting.

## Acceptance Criteria

1. The four command shapes in the creative decision rank the scoped set, and the unfiltered command still uses HNSW.
2. A regression test fails on the post-filtered HNSW shape: a nearer outsider does not hide an insider.
3. Bad `--role` exits 2. Unknown `--harness` exits 0 with an empty result.
4. `sr-semantic` and `sr-search` describe the two scopes and the empty-result meaning.
5. Reflect is complete and a non-draft pull request is open.

## Rework

Review [5420273503](https://github.com/Texarkanine/stockroom/pull/136#pullrequestreview-5420273503) on pull request 136. The engine behavior stays. The human docs listed `--harness` and `--role` in three places that are not the flag home.

1. `docs/advanced/cli.md`: the table column is the subcommand's job, named Role. Do not define speaker `--role` in that cell. The page does not fork skill flag tables.
2. `docs/user-guide/search.md`: operational flags live in each skill. This page does not duplicate them.
3. `docs/user-guide/skills.md`: the index line is another listing. One home, not four.

The flag home is `skills/sr-semantic/SKILL.md`, which already has the pronoun map. `sr-search` keeps its route row. Architecture keeps the two-path sentence. No engine or test change.
