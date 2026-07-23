# Task: cursor-ai-tracking-multi-db (PR #85 rework)

* Task ID: cursor-ai-tracking-multi-db
* Complexity: Level 1
* Type: PR feedback rework

## Fix

PR #85 judge items 1, 3, 4, 5:

1. **Docs** — `docs/user-guide/installed-layout.md`: optional-settings row documents `$XDG_CONFIG_HOME/...` and `~/.config/stockroom/config.toml` default.
2. **Env override** — `resolve_db_paths` returns `Path(override).expanduser()`; test `test_resolve_db_paths_env_override_expands_user`.
3. **Config parse warning** — `config.load_settings` logs WARNING on UTF-8/TOML decode failure, still returns empty `Settings()`; test `test_load_settings_malformed_toml_logs_warning`.
4. **Normalize** — `_normalize_db_path` uses `path.expanduser()` (no `Path(path)` wrap).

### Files
- `docs/user-guide/installed-layout.md`
- `skills/sr-search/src/stockroom/ingest/enrich.py`
- `skills/sr-search/src/stockroom/config.py`
- `skills/sr-search/tests/test_ingest_enrich.py`
- `skills/sr-search/tests/test_config.py`

### Verify
- Full suite: 672 passed, 1 skipped (`uv run --no-sync pytest`)

### Out of scope
- Item 2 (reflection suite count), item 10 (shared seed helper)
- Doctor smoke → ensure-env remedy → [#86](https://github.com/Texarkanine/stockroom/issues/86)

## QA
- PASS: all four rework items present; fail-soft contract preserved; no debris; docs row matches `ingest.md` / `resolve_config_home`.

## Status
- [x] Build
- [x] QA
