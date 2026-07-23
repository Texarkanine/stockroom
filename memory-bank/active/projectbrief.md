# Project Brief

## User Story

As a stockroom operator on WSL + Windows Cursor, I want ingest to merge model enrichment from every readable `ai-code-tracking.db` (CLI and IDE) so that `sessions.models` stays populated for both corpora and re-ingest does not wipe IDE models when a tiny WSL tracking DB appears.

## Use-Case(s)

### Use-Case 1

Default `stockroom ingest` (no `STOCKROOM_AI_TRACKING_DB`) on a machine with both `~/.cursor/ai-tracking/ai-code-tracking.db` (CLI) and a Windows IDE tracking DB under `/mnt/...` — both contribute models for their respective `conversationId`s.

### Use-Case 2

Operator pins an odd-path tracking DB via XDG `[cursor].ai_tracking_dbs`; that pin is additive to discovery (missing/unreadable paths fail-soft).

### Use-Case 3

Tests / one-shots set `STOCKROOM_AI_TRACKING_DB` to force a single DB (override walk/merge).

## Requirements

1. Fix [#82](https://github.com/Texarkanine/stockroom/issues/82) as specified there: walk/merge all readable ai-tracking candidates (fail-soft), not first-hit.
2. Optional additive XDG config list `ai_tracking_dbs`; create XDG config fresh if needed (reference aborted `enhance-cursor-tokens` only for prior XDG patterns).
3. Keep `STOCKROOM_AI_TRACKING_DB` as single-DB override for tests/one-shots.
4. Implement on current branch `wsl-dual-sot` (not `enhance-cursor-tokens`).

## Constraints

1. Out of scope: Cursor `state.vscdb` token enrich; Claude token ingest; [#84](https://github.com/Texarkanine/stockroom/issues/84) historical backfill.
2. Do not revive aborted enrich/`state_vscdb` work from `enhance-cursor-tokens`.
3. Singular `state_vscdb` policy (if any) remains unchanged — do not turn it into a multi-path walk.

## Acceptance Criteria

1. With both a WSL CLI tracking DB and a Windows IDE tracking DB present, default ingest populates `sessions.models` from both corpora for matching `session_id`s.
2. Configured `ai_tracking_dbs` entries are included even when not found by discovery; missing/unreadable paths stay fail-soft.
3. Re-ingest of an IDE session after the WSL DB appears does not wipe models that still exist in the IDE tracking DB.
4. Docs describe multi-DB merge and the additive config list.
5. Tests cover: two synthetic DBs with disjoint IDs → merged enrich; shadowing first-hit regression; config pins additive to discovery.

## Rework

PR #85 review feedback (selected items from judge pass):

1. **Docs:** `installed-layout.md` optional-settings row must mention both `$XDG_CONFIG_HOME/stockroom/config.toml` and the `~/.config/stockroom/config.toml` default fallback.
2. **Env override:** `resolve_db_paths` must `.expanduser()` the `STOCKROOM_AI_TRACKING_DB` path (parity with config pins).
3. **Config parse visibility:** when a present `config.toml` fails UTF-8/TOML decode, log a warning then still return empty `Settings()` (fail-soft contract unchanged).
4. **Normalize clarity:** `_normalize_db_path` should call `path.expanduser()` without wrapping `Path(path)`.

Out of scope for this rework: reflection suite-count line, shared test seed helper, other dismissed review nits.
