# Warehouse schema

Logical relationships only — DuckDB has no FOREIGN KEY constraints (deliberate).

```mermaid
erDiagram
    _sync_state {
        VARCHAR harness PK
        VARCHAR source_root PK
        TIMESTAMP last_mtime
        VARCHAR last_path
        TIMESTAMP updated_at
    }
    embeddings {
        VARCHAR harness PK
        VARCHAR owner_table PK
        VARCHAR owner_id PK
        INTEGER chunk_index PK
        VARCHAR embed_model
        FLOAT_384 vector
    }
    messages {
        VARCHAR harness PK
        VARCHAR session_id PK
        VARCHAR message_id PK
        VARCHAR parent_id
        INTEGER ordinal
        VARCHAR role
        VARCHAR text
        VARCHAR model
        TIMESTAMP ts
        BIGINT input_tokens
        BIGINT output_tokens
        BIGINT cache_creation_tokens
        BIGINT cache_read_tokens
        VARCHAR source_uuid
        TIMESTAMP first_seen_at
    }
    session_token_usage["session_token_usage (view)"] {
        VARCHAR harness
        VARCHAR session_id
        HUGEINT input_tokens_from_messages
        HUGEINT output_tokens_from_messages
        HUGEINT cache_creation_tokens_from_messages
        HUGEINT cache_read_tokens_from_messages
        BIGINT input_tokens_native
        BIGINT output_tokens_native
        BIGINT cache_creation_tokens_native
        BIGINT cache_read_tokens_native
        HUGEINT input_tokens_total
        HUGEINT output_tokens_total
        HUGEINT cache_creation_tokens_total
        HUGEINT cache_read_tokens_total
        VARCHAR token_grain
    }
    sessions {
        VARCHAR harness PK
        VARCHAR session_id PK
        VARCHAR cwd
        VARCHAR git_branch
        VARCHAR source_path
        BOOLEAN is_subagent
        VARCHAR parent_session_id
        VARCHAR agent_id
        VARCHAR agent_type
        VARCHAR spawning_tool_use_id
        VARCHAR agent_name
        VARCHAR_ARRAY models
        VARCHAR title
        VARCHAR harness_version
        TIMESTAMP started_at
        TIMESTAMP ended_at
        VARCHAR project_id
        TIMESTAMP source_mtime
        VARCHAR workspace_key
        BIGINT input_tokens
        BIGINT output_tokens
        BIGINT cache_creation_tokens
        BIGINT cache_read_tokens
        VARCHAR entrypoint
    }
    tool_calls {
        VARCHAR harness PK
        VARCHAR session_id PK
        VARCHAR message_id PK
        INTEGER ordinal PK
        VARCHAR tool_name
        JSON tool_input
        VARCHAR source_tool_use_id
    }
    messages ||--o{ embeddings : "owner_table=messages"
    messages ||--o{ tool_calls : ""
    sessions ||--o{ messages : ""
    sessions ||--o{ session_token_usage : "rolls up"
    tool_calls ||--o{ embeddings : "owner_table=tool_calls"
```

Indexes (including the embeddings HNSW index) are omitted; they are snapshot data, not query-forming structure.
