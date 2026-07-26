# Harness Sources

Where [ingest](basic.md#ingest) reads each harness's history from, how to point it somewhere else, and the per-harness quirks worth knowing about.

## Cursor

Cursor has two transcript roots, watermarked independently:

| What | Default | Override |
| --- | --- | --- |
| IDE agent transcripts | `~/.cursor/projects` | `STOCKROOM_CURSOR_ROOT` |
| Agent CLI chats | `~/.cursor/chats` | `STOCKROOM_CURSOR_CHATS_ROOT` |

Overrides are environment variables on the ingest command:

```bash
STOCKROOM_CURSOR_ROOT=/path/to/cursor/projects stockroom ingest
STOCKROOM_CURSOR_CHATS_ROOT=/path/to/cursor/chats stockroom ingest
```

### Best-Effort Parsing

Cursor Agent CLI chats (`~/.cursor/chats/**/store.db`) are parsed best-effort: if a store is locked, corrupt, or its internal blob layout drifts, that session is skipped and the rest of the ingest continues (the chats watermark does not advance past a skipped store, so a later run can retry). Empty or meta-only stores still upsert a session with zero messages. Fixture tests in the repo fail loudly when the known layout changes — operators should not expect a hard ingest failure from layout drift alone.

### Cursor `sessions.models` Enrichment

Cursor has no in-band session model grain. When available, ingest fills `sessions.models` from Cursor's optional `ai-code-tracking.db` sidecar(s).

**Default ingest walks and merges every readable candidate:**

* Linux/Mac paths under `~/.cursor/`
* WSL Windows-home mounts under `/mnt/<drive>/Users/*/.cursor/...`

Optional **additive** pins (if you've got a weird setup) live in XDG config — `$XDG_CONFIG_HOME/stockroom/config.toml` or `~/.config/stockroom/config.toml`:

```toml
[cursor]
ai_tracking_dbs = [
  "/some/funky/path/.cursor/ai-tracking/ai-code-tracking.db",
]
```

Pins are unioned with discovery (not a replacement). Missing pins fail soft.

For tests or one-shots, `STOCKROOM_AI_TRACKING_DB` forces a **single** DB and disables the multi-path walk:

```bash
STOCKROOM_AI_TRACKING_DB=/path/to/ai-code-tracking.db stockroom ingest
```

## Claude Code

Claude Code has one transcript root:

| What | Default | Override |
| --- | --- | --- |
| Project transcripts | `~/.claude/projects` | `STOCKROOM_CLAUDE_ROOT` |

```bash
STOCKROOM_CLAUDE_ROOT=/path/to/claude/projects stockroom ingest
```

Claude transcripts carry model and token usage in-band, per message, so there is no sidecar to discover. Model attribution lands in `messages.model`; `sessions.models` stays empty because Claude's model grain is per-message.
