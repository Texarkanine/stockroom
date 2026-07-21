# Project Brief

## User Story

As a stockroom user, I want Cursor Agent CLI chats and Claude Code surface provenance (`entrypoint`) reflected in the warehouse under the existing harness brands, so that dashboard and naive queries include CLI history with Cursor, while I can still distinguish IDE vs CLI vs desktop when I care.

## Use-Case(s)

### Use-Case 1

A user runs Cursor Agent CLI (`~/.cursor/chats/**/store.db`). After ingest, those sessions appear as `harness='cursor'` with `entrypoint='cli'`, including in the dashboard and ordinary SQL.

### Use-Case 2

A user queries Claude sessions and filters or groups by `entrypoint` (`cli`, `claude-desktop`, or other native values) without changing `harness='claude'`.

### Use-Case 3

The same Cursor `session_id` exists in both `~/.cursor/chats/.../store.db` and `agent-transcripts`. Ingest counts it once, preferring the chats `store.db` as authoritative.

## Requirements

1. Ingest Cursor Agent CLI sessions from `~/.cursor/chats/<hash>/<uuid>/store.db` into the warehouse under `harness='cursor'`.
2. Add a session-level `entrypoint` column on `sessions`.
3. For Claude JSONL already under `~/.claude`, pass through the native `entrypoint` field (e.g. `cli`, `claude-desktop`) when present; otherwise leave null / pass unknown raw values as appropriate.
4. For Cursor, synthesize `entrypoint` from source provenance only: `cli` for chats `store.db`, `ide` for `agent-transcripts` (no system-prompt heuristics).
5. When the same Cursor `session_id` appears in both chats and `agent-transcripts`, ingest once preferring `store.db`.
6. No dashboard UI changes in this task (column available to SQL / naive queries; harness umbrella unchanged).

## Constraints

1. Linux-first roots only (`~/.cursor`, `~/.claude`). Do not special-case WSL/Windows multi-home discovery; Windows-only conversations may remain missing.
2. Do not sniff Cursor system prompts to detect CLI; path/provenance only.
3. Keep brand/harness as `cursor` / `claude`; surface distinction is `entrypoint` only.
4. Follow project TDD and existing ingest/migration patterns.

## Acceptance Criteria

1. CLI chats from `~/.cursor/chats` are discoverable and ingestible as `harness='cursor'`, `entrypoint='cli'`.
2. Existing Cursor `agent-transcripts` sessions get `entrypoint='ide'` (synthesized).
3. Claude sessions persist native `entrypoint` when present in JSONL.
4. Collision on Cursor `session_id` across chats + transcripts does not double-count messages; `store.db` wins.
5. Schema migration adds `sessions.entrypoint`; tests and ingest writer cover the new field.
6. Dashboard code is unchanged; warehouse/SQL can distinguish entrypoints.
