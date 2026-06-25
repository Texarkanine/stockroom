-- stockroom warehouse — initial schema (migration 0001)
--
-- Design invariants encoded here:
--   * Identity is uniform: message_id = '{session_id}#{ordinal}' for every
--     harness (a deterministic surrogate). Native ids are demoted to
--     `source_*` provenance columns and are never joined on.
--   * One meaning per column, independent of harness; where a value only
--     exists at a different grain per harness (model), separate grain-specific
--     columns are used (messages.model vs sessions.models) and each harness
--     fills only the grain it actually has.
--   * Typed columns for anything queried/aggregated (token usage = four BIGINT
--     columns; model sets = native VARCHAR[] LIST). JSON is reserved for the
--     irreducibly heterogeneous payloads such as tool_calls.tool_input.
--   * Tool INPUTS only — never outputs. Thinking is also not captured.
--
-- Deliberately NOT here (by design, documented in the plan):
--   * No DB-level FOREIGN KEY constraints — DuckDB FK enforcement is limited
--     and complicates bulk-ETL insert ordering; logical relationships are
--     enforced in the ingest layer (milestone 3) and asserted via tests.
--   * No CHECK on `harness` — hard-coding the known set would block
--     future-harness onboarding (extensibility invariant).
--   * No HNSW/VSS index on embeddings — that needs the VSS extension (Phase 2);
--     0001 defines the table and FLOAT[384] column only.

-- One row per conversation. Subagents are their own session rows linked to a
-- parent via parent_session_id.
CREATE TABLE sessions (
    harness              TEXT,        -- 'cursor' | 'claude' | future harness
    session_id           TEXT,        -- cursor: conv-id from path; claude: sessionId
    project_path         TEXT,        -- decoded from the encoded project dir
    cwd                  TEXT,        -- claude: cwd; cursor: derived from project_path
    git_branch           TEXT,        -- claude only
    source_path          TEXT    NOT NULL,  -- absolute path to the .jsonl (provenance + watermark)
    is_subagent          BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE for subagent sessions
    parent_session_id    TEXT,        -- subagent -> parent conversation
    agent_id             TEXT,        -- claude: agentId; cursor: subagent file id
    agent_type           TEXT,        -- claude: agentType/attributionAgent; cursor: Task.subagent_type
    spawning_tool_use_id TEXT,        -- claude: meta.json toolUseId; cursor: NULL (structural only)
    agent_name           TEXT,        -- claude agent-name
    models               VARCHAR[],   -- conversation-grained model set (cursor); claude: NULL
    title                TEXT,        -- claude ai/custom title; cursor NULL (enrich)
    harness_version      TEXT,        -- claude version; cursor NULL
    started_at           TIMESTAMP,   -- claude min(ts); cursor NULL/mtime
    ended_at             TIMESTAMP,   -- claude max(ts); cursor NULL/mtime
    PRIMARY KEY (harness, session_id)
);

-- The message-identity contract + reconstruction keys. Column meanings are
-- harness-independent; per-harness extraction differs but yields one meaning.
CREATE TABLE messages (
    harness               TEXT,
    session_id            TEXT,
    message_id            TEXT,       -- UNIFORM '{session_id}#{ordinal}', deterministic
    parent_id             TEXT,       -- message_id of the parent; NULL for roots
    ordinal               INTEGER NOT NULL,  -- 0-based position in session, conversation order
    role                  TEXT    NOT NULL,  -- 'user' | 'assistant'
    text                  TEXT,       -- the turn's text, stored whole (thinking NOT captured)
    model                 TEXT,       -- model that produced THIS MESSAGE (claude); cursor NULL
    ts                    TIMESTAMP,  -- wall-clock time (claude); cursor NULL
    input_tokens          BIGINT,     -- message.usage.input_tokens (claude); cursor NULL
    output_tokens         BIGINT,     -- message.usage.output_tokens
    cache_creation_tokens BIGINT,     -- message.usage.cache_creation_input_tokens
    cache_read_tokens     BIGINT,     -- message.usage.cache_read_input_tokens
    source_uuid           TEXT,       -- provenance only (claude uuid); NOT a join key
    PRIMARY KEY (harness, session_id, message_id)
);

-- Tool INPUTS only — never outputs. Tool calls are children of a message turn.
CREATE TABLE tool_calls (
    harness            TEXT,
    session_id         TEXT,
    message_id         TEXT,          -- the turn that emitted this tool_use
    ordinal            INTEGER,       -- block index of this tool_use within its turn
    tool_name          TEXT NOT NULL,
    tool_input         JSON NOT NULL, -- stored whole, untruncated
    source_tool_use_id TEXT,          -- provenance: claude 'toolu_...' id; cursor NULL
    PRIMARY KEY (harness, session_id, message_id, ordinal)
);

-- Forward-declared; populated in Phase 2 (embeddings + search). No HNSW index.
CREATE TABLE embeddings (
    harness     TEXT,
    owner_table TEXT,                 -- 'messages' | 'tool_calls'
    owner_id    TEXT,                 -- references the owner row's message_id
    chunk_index INTEGER,
    embed_model TEXT NOT NULL,
    vector      FLOAT[384],           -- VSS/HNSW index added in Phase 2
    PRIMARY KEY (harness, owner_table, owner_id, chunk_index)
);

-- Incremental-ingest watermark + non-append mutation detector (per source root).
CREATE TABLE _sync_state (
    harness     TEXT,
    source_root TEXT,
    last_mtime  TIMESTAMP,
    last_path   TEXT,
    updated_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (harness, source_root)
);
