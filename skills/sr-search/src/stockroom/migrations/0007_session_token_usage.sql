-- stockroom warehouse — dual-grain session token columns + rollup VIEW (migration 0007)
--
-- Adds nullable session-grain token columns on `sessions` (parallel to
-- `messages.*_tokens`) for harnesses that report conversation-level usage.
-- Claude and Cursor leave these NULL today; ingest must never invent them from
-- message sums (and must never invent message tokens from session totals).
--
-- VIEW `session_token_usage` is the read-time rollup surface:
--   * `*_from_messages` — SUM of non-null message token columns per session
--   * `*_native`        — passthrough of `sessions.*_tokens`
--   * `*_total`         — COALESCE(native, from_messages)
--   * `token_grain`     — 'session' | 'message' | 'none'
--
-- Structural only — NO backfill DML. Pre-existing rows keep session tokens
-- NULL. Writers target base tables only; the VIEW is read-only. No secondary
-- index (personal-scale DuckDB; messages PK already leads with session).

ALTER TABLE sessions ADD COLUMN input_tokens BIGINT;
ALTER TABLE sessions ADD COLUMN output_tokens BIGINT;
ALTER TABLE sessions ADD COLUMN cache_creation_tokens BIGINT;
ALTER TABLE sessions ADD COLUMN cache_read_tokens BIGINT;

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
