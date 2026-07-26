# Load the Warehouse

## Harness-Specific Notes

### Cursor

#### Best-Effort Parsing

Cursor Agent CLI chats (`~/.cursor/chats/**/store.db`) are parsed best-effort: if a store is locked, corrupt, or its internal blob layout drifts, that session is skipped and the rest of the ingest continues (the chats watermark does not advance past a skipped store, so a later run can retry). Empty or meta-only stores still upsert a session with zero messages. Fixture tests in the repo fail loudly when the known layout changes — operators should not expect a hard ingest failure from layout drift alone.

```bash
stockroom ingest              # both harnesses, incremental
stockroom ingest --full       # ignore watermarks; re-read everything (still idempotent)
stockroom ingest --verbose    # progress lines (quiet by default)
```

`--harness cursor` or `--harness claude` limits to one source. Non-default transcript roots are env overrides on the same command:

```bash
STOCKROOM_CURSOR_ROOT=/path/to/cursor/projects stockroom ingest
STOCKROOM_CURSOR_CHATS_ROOT=/path/to/cursor/chats stockroom ingest
STOCKROOM_CLAUDE_ROOT=/path/to/claude/projects stockroom ingest
```

Defaults are `~/.cursor/projects`, `~/.cursor/chats`, and `~/.claude/projects`.

`sr-initialize` runs `stockroom ingest --full` once so you are not waiting for the first nightly job. On years of history that first pass can take many minutes (varying greatly depending on your machine's CPU and disk speed); it prints per-harness session/message/tool_call counts when done.

#### Cursor `sessions.models` Enrichment

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
