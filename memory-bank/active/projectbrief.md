# Project Brief

## User Story

As a stockroom user running nightly ingest-then-embed, I want session rewrite to invalidate only embeddings whose message text changed (or whose messages were removed) so that append-only growth and embed lag do not wipe the semantic index for unchanged history.

## Use-Case(s)

### Use-Case 1

Nightly mtime bump re-ingests an active session with only new turns appended. Prior message embeddings remain; only new message ids lack vectors until embed runs.

### Use-Case 2

Ingest succeeds but embed fails (`torch` missing, etc.). Semantic search still returns useful results for the bulk of already-embedded history; only new/changed turns are missing vectors.

### Use-Case 3

A message at an existing `message_id` has its text edited. That id's embeddings are deleted; sibling unchanged messages keep theirs. Removed message ids lose their embeddings. Other sessions are untouched.

## Requirements

1. On session rewrite, load old message texts and compare to new texts before delete-then-insert.
2. Delete embeddings only for message ids that were removed or whose text changed.
3. Leave embeddings for unchanged `message_id`s alone.
4. Remove the blanket embedding delete from `_delete_session`.
5. Keep embed selection as-is (`NOT EXISTS` current-model vector; `--full` still re-embeds everything).
6. No schema migration.
7. Extend/replace `test_rewriting_session_cascades_embedding_delete` to lock the new contract.

## Constraints

1. No soft-stale search of changed text.
2. No content-hash column migration.
3. Do not merge ingest+embed into one transaction.
4. Solution is compare-and-keep by text in the ingest writer (issue option B).

## Acceptance Criteria

1. Rewriting a session with identical message texts retains existing embeddings for those `message_id`s.
2. Append-only growth retains embeddings for prior messages; only new ids lack vectors until embed.
3. Changing text at the same `message_id` deletes that id's embeddings (siblings retained).
4. Removed message ids lose their embeddings.
5. Other sessions' embeddings are never touched.
6. Existing embed `NOT EXISTS` / `--full` behavior still green; no migration required.
7. Extend/replace `test_rewriting_session_cascades_embedding_delete` to lock the new contract.

## Source

https://github.com/Texarkanine/stockroom/issues/43
