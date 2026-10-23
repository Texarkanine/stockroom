-- stockroom warehouse — frozen schema at version 9 (new warehouses)
--
-- A new warehouse is built from this file, not by running the migrations.
-- It holds the schema the chain 0001 to 0009 leaves, with two differences
-- that change storage only:
--   * No vector index. 0003 created one and 0009 drops it.
--   * messages.text and tool_calls.tool_input use zstd compression.
-- Columns keep the order the chain leaves them in, and the view is 0007's
-- text word for word. A test keeps this file equal to the chain at 9.
--
-- Frozen: once a release carries this file, its SQL never changes (comments
-- may). A schema change is a new migration. The ERD edges (@rel) live in the
-- migrations' comments only.

CREATE TABLE sessions (
    harness               TEXT,
    session_id            TEXT,
    cwd                   TEXT,
    git_branch            TEXT,
    source_path           TEXT    NOT NULL,
    is_subagent           BOOLEAN NOT NULL DEFAULT FALSE,
    parent_session_id     TEXT,
    agent_id              TEXT,
    agent_type            TEXT,
    spawning_tool_use_id  TEXT,
    agent_name            TEXT,
    models                VARCHAR[],
    title                 TEXT,
    harness_version       TEXT,
    started_at            TIMESTAMP,
    ended_at              TIMESTAMP,
    project_id            TEXT,
    source_mtime          TIMESTAMP,
    workspace_key         TEXT,
    input_tokens          BIGINT,
    output_tokens         BIGINT,
    cache_creation_tokens BIGINT,
    cache_read_tokens     BIGINT,
    entrypoint            TEXT,
    PRIMARY KEY (harness, session_id)
);

CREATE TABLE messages (
    harness               TEXT,
    session_id            TEXT,
    message_id            TEXT,
    parent_id             TEXT,
    ordinal               INTEGER NOT NULL,
    role                  TEXT    NOT NULL,
    text                  TEXT    USING COMPRESSION zstd,
    model                 TEXT,
    ts                    TIMESTAMP,
    input_tokens          BIGINT,
    output_tokens         BIGINT,
    cache_creation_tokens BIGINT,
    cache_read_tokens     BIGINT,
    source_uuid           TEXT,
    first_seen_at         TIMESTAMP,
    PRIMARY KEY (harness, session_id, message_id)
);

CREATE TABLE tool_calls (
    harness            TEXT,
    session_id         TEXT,
    message_id         TEXT,
    ordinal            INTEGER,
    tool_name          TEXT NOT NULL,
    tool_input         JSON USING COMPRESSION zstd NOT NULL,
    source_tool_use_id TEXT,
    PRIMARY KEY (harness, session_id, message_id, ordinal)
);

CREATE TABLE embeddings (
    harness     TEXT,
    owner_table TEXT,
    owner_id    TEXT,
    chunk_index INTEGER,
    embed_model TEXT NOT NULL,
    vector      FLOAT[384],
    PRIMARY KEY (harness, owner_table, owner_id, chunk_index)
);

CREATE TABLE _sync_state (
    harness     TEXT,
    source_root TEXT,
    last_mtime  TIMESTAMP,
    last_path   TEXT,
    updated_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (harness, source_root)
);

CREATE VIEW session_token_usage AS
SELECT
    s.harness,
    s.session_id,
    m.input_tokens_from_messages,
    m.output_tokens_from_messages,
    m.cache_creation_tokens_from_messages,
    m.cache_read_tokens_from_messages,
    s.input_tokens AS input_tokens_native,
    s.output_tokens AS output_tokens_native,
    s.cache_creation_tokens AS cache_creation_tokens_native,
    s.cache_read_tokens AS cache_read_tokens_native,
    COALESCE(s.input_tokens, m.input_tokens_from_messages) AS input_tokens_total,
    COALESCE(s.output_tokens, m.output_tokens_from_messages) AS output_tokens_total,
    COALESCE(s.cache_creation_tokens, m.cache_creation_tokens_from_messages)
        AS cache_creation_tokens_total,
    COALESCE(s.cache_read_tokens, m.cache_read_tokens_from_messages)
        AS cache_read_tokens_total,
    CASE
        WHEN s.input_tokens IS NOT NULL
            OR s.output_tokens IS NOT NULL
            OR s.cache_creation_tokens IS NOT NULL
            OR s.cache_read_tokens IS NOT NULL
            THEN 'session'
        WHEN m.input_tokens_from_messages IS NOT NULL
            OR m.output_tokens_from_messages IS NOT NULL
            OR m.cache_creation_tokens_from_messages IS NOT NULL
            OR m.cache_read_tokens_from_messages IS NOT NULL
            THEN 'message'
        ELSE 'none'
    END AS token_grain
FROM sessions AS s
LEFT JOIN (
    SELECT
        harness,
        session_id,
        SUM(input_tokens) AS input_tokens_from_messages,
        SUM(output_tokens) AS output_tokens_from_messages,
        SUM(cache_creation_tokens) AS cache_creation_tokens_from_messages,
        SUM(cache_read_tokens) AS cache_read_tokens_from_messages
    FROM messages
    GROUP BY harness, session_id
) AS m
    ON s.harness = m.harness AND s.session_id = m.session_id;
