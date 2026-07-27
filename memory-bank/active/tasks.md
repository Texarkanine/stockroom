# Current Task: fix-cursor-cli-wal-ingest

**Complexity:** Level 1

## Bug

Cleanly-closed Cursor CLI `store.db` files are WAL-mode databases with `-wal`/`-shm` removed. Opening with `?mode=ro` alone can fail with `SQLITE_CANTOPEN` on some SQLite builds (cannot create `-shm`), and `parse_session` swallowed that into `None` — silent data loss ([issue #95](https://github.com/Texarkanine/stockroom/issues/95)).

## Fix

- Added `_READ_URIS` + `_read_store`: try `mode=ro`, then `mode=ro&immutable=1`; retry wraps the whole read (lazy open).
- `parse_session` uses `_read_store`; still returns `None` when both strategies fail.

## Files

- `skills/sr-search/src/stockroom/ingest/cursor_chats.py`
- `skills/sr-search/tests/test_ingest_cursor_chats.py`

## Verification

- [x] WAL-at-rest fixture parses
- [x] Sidecars-present path still works
- [x] Mocked `mode=ro` failure falls back to `immutable=1`
- [x] Corrupt file → `_read_store` returns `None`
- [x] Full suite: 789 passed, 2 skipped
