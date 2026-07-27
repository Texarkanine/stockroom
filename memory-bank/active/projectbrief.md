# Project Brief

## User Story

As a stockroom user, I want Cursor CLI chat sessions to ingest reliably after a clean close so that finished CLI conversations appear in the warehouse instead of being silently dropped.

## Use-Case(s)

### Cleanly-closed Cursor CLI store

A Cursor CLI session writes `~/.cursor/chats/.../store.db` in WAL mode, then checkpoints and removes `-wal`/`-shm` on clean close. `stockroom ingest` must still parse that at-rest store into a session with messages and tool calls.

### Live Cursor CLI store

While a session is still open (sidecars present), ingest continues to use the existing `mode=ro` path and reads whatever has been committed so far.

### Genuinely unreadable store

A corrupt or otherwise unreadable `store.db` still skips (returns `None`) without aborting the batch.

## Requirements

1. Fix `stockroom.ingest.cursor_chats` so cleanly-closed WAL-mode stores are readable ([issue #95](https://github.com/Texarkanine/stockroom/issues/95)).
2. Try `mode=ro` first; on failure retry the whole read with `mode=ro&immutable=1`.
3. Preserve skip-not-abort when both strategies fail.
4. Add a regression test whose fixture uses `PRAGMA journal_mode=WAL` and then removes `-wal`/`-shm` sidecars.
5. Keep coverage for the sidecars-present (`mode=ro`) path.

## Constraints

1. Do not switch to copy-to-tempdir as the default open strategy.
2. Do not replace `mode=ro` with `immutable=1` as a blanket open (live sessions need WAL visibility).
3. Out of scope unless trivial: ingest-summary skip counts; watermark per-file redesign; orphaned-`-wal`-without-`-shm` special-casing (accepted staleness per the issue).

## Acceptance Criteria

1. WAL-at-rest fixture: `parse_session` returns a populated session, not `None`.
2. Sidecars-present path still exercises `mode=ro` successfully.
3. Genuinely corrupt store: `_read_store` / `parse_session` returns `None` (skip, not raise).
4. After fix, a normal `stockroom ingest` can backfill previously unreadable CLI chats without requiring `--full` (watermark for chats root was never advanced while stores were skipped).
