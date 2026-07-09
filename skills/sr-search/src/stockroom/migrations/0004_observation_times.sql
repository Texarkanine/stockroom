-- stockroom warehouse — durable observation times (migration 0004)
--
-- Adds two uniform time meanings without fabricating source-authored times:
--
--   * sessions.source_mtime — provenance: the mtime of the session's source
--     transcript when that session was last ingested. It is the durable,
--     best-available activity fallback for harnesses without record times.
--   * messages.first_seen_at — observation time: when stockroom first observed
--     this message. The writer carries this value forward by message_id across
--     re-ingest and seeds new rows from source_mtime.
--
-- Both columns are nullable because existing rows cannot be honestly backfilled
-- by DDL alone. Ingest populates them when a source is next observed. Forward-
-- only: earlier migrations and their snapshots remain frozen.
ALTER TABLE sessions ADD COLUMN source_mtime TIMESTAMP;
ALTER TABLE messages ADD COLUMN first_seen_at TIMESTAMP;
