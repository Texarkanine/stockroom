# Creative — Schema Field Enumeration + Draft DDL

**Task:** `p1-data-backbone` milestone 1 (Schema field enumeration + locked DDL), L3 sub-run.
**Status:** DRAFT — stopped for operator review per explicit instruction, *before* any DDL is locked.
**Evidence:** raw machine-generated enumerations in `./evidence/` (`cursor-field-enumeration.txt`, `claude-field-enumeration.txt`, `enumerator.py`). Derived empirically from the harnesses' own on-disk formats — clean-room compliant (no `claude-warehouse`; `cursor-warehouse.duckdb` deliberately *not* read as a schema source).

## 1. Where the data lives (on-disk, this machine)

| Harness | Transcript path | Subagents | Per-record metadata |
|---|---|---|---|
| **Cursor** (IDE agent) | `~/.cursor/projects/<enc-path>/agent-transcripts/<conv-id>/<conv-id>.jsonl` | `…/<conv-id>/subagents/<subagent-conv-id>.jsonl` | **none** (only `role` + `message`) |
| **Claude Code** | `~/.claude/projects/<enc-path>/<session-id>.jsonl` | `…/<session-id>/subagents/agent-<agentId>.jsonl` + `agent-<agentId>.meta.json` | rich (uuid, parentUuid, timestamp, model, usage, cwd, gitBranch, version…) |

Corpus enumerated: **Cursor** 713 files / 25,065 records; **Claude** 39 files / 4,158 records. Both are JSONL event streams (one JSON object per line); line order *is* the ordering signal.

**Secondary / not-a-transcript sources (noted, not the schema basis):**
- `~/.cursor/chats/<hash>/<id>/store.db` — the Cursor **CLI** agent (SQLite), a *different* format from the IDE `agent-transcripts`. Out of scope for this enumeration; flag for ingest.
- `~/.cursor/cursor-warehouse.duckdb` — operator's *derived* warehouse (provenance-sensitive). Not read.
- Cursor's `ai-code-tracking.db` (model/labeling enrichment named by the roadmap) is **not present in the WSL home** — it lives on the Windows side. This is the empirical confirmation of the roadmap's "WSL/Windows-mount-aware path resolution" and "*optional* model/labeling enrichment" caveats: **Cursor's model + timestamps are simply absent from the on-disk transcript** and must be enriched (or left NULL) at ingest.

## 2. The headline finding: the two formats are wildly asymmetric

- **Claude Code is self-describing.** Every content record carries `uuid`, `parentUuid` (threading), `sessionId`, `timestamp`, `message.model`, `message.usage.*`, `cwd`, `gitBranch`, `version`, plus subagent identity (`agentId`, `isSidechain`) and explicit tool-call ids.
- **Cursor's transcript is a bare message list.** The *only* top-level keys are `role` and `message` (plus a `turn_ended` status marker). **No ids, no parent pointers, no timestamps, no model, no token usage.** Identity and ordering must be **synthesized** from `(conversation-id-from-path, line-ordinal)`.

This asymmetry is the central schema design force: the shared, harness-labeled tables must treat the *Claude-native* columns (uuid, parent, model, time, usage) as **nullable / synthesized** for Cursor. The "stable message-identity contract" the brief demands is, concretely, *the rule for minting deterministic surrogate ids for Cursor and adopting native uuids for Claude.*

### Subagent ↔ parent linkage is also asymmetric

| | Claude Code | Cursor |
|---|---|---|
| Subagent file | `subagents/agent-<agentId>.jsonl` | `subagents/<subagent-conv-id>.jsonl` |
| In-record agent id | `agentId` on records; `isSidechain=true` | none (file is a bare message list) |
| Parent→child link | **explicit**: `agent-<id>.meta.json` → `{agentType, description, toolUseId}`; `toolUseId` points at the parent's `tool_use.id` | **structural only**: child file sits in the parent conversation's `subagents/` dir; parent `Task` tool_use has no child id (only `resume` references a *prior* subagent id) |
| Cross-session fork | `fork-context-ref` `{parentSessionId, parentLastUuid, agentId, contextLength}` | n/a observed |

## 3. ALL fields that exist (complete enumeration)

Legend: **KEEP** = goes in the locked schema · **DERIVE** = synthesized (not literally on disk) · **ENRICH** = filled later from a side source, NULL otherwise · **DROP** = exists but deliberately not stored (with reason).

### 3a. Cursor — `agent-transcripts/*.jsonl` (3 record kinds)

**`role:user` / `role:assistant`** (the only content-bearing records):

| On-disk field | Disposition | Target |
|---|---|---|
| `role` | KEEP | `messages.role` |
| `message.content[text].text` | KEEP | `messages` text content |
| `message.content[text].type` (`"text"`) | DROP (discriminator only) | — |
| `message.content[tool_use].name` | KEEP | `tool_calls.tool_name` |
| `message.content[tool_use].input` (+ all `…input.*` leaves: `command`, `path`, `pattern`, `glob`, `old_string`/`new_string`, `contents`, `todos[]`, `questions[]`, `prompt`, `subagent_type`, `resume`, `url`, `query`, `target_directories[]`, … — full list in evidence) | KEEP (stored **whole** as JSON, untruncated, **inputs only**) | `tool_calls.tool_input` |
| `message.content[tool_use].type` (`"tool_use"`) | DROP (discriminator) | — |
| `message.content[tool_use].input.todos[]` (TodoWrite) | KEEP — candidate `plan_documents` source (see Q3) | `plan_documents`? |
| *(no message id)* | DERIVE | `messages.message_uid` (synthesized) |
| *(no parent)* | DERIVE | `messages.parent_uid` = prior line |
| *(no ordinal)* | DERIVE | `messages.ordinal` = line index |
| *(no model)* | ENRICH | `messages.model` (NULL on disk) |
| *(no timestamp)* | ENRICH | `messages.ts` (NULL; file mtime as coarse fallback) |
| *(no tool_use id)* | DERIVE | `tool_calls.tool_use_id` (synthesized) |

**`role:turn_ended`** — `{type:"turn_ended", status, error}`. Turn boundary / abort marker. Disposition: **DROP** as content; optionally surface `error`/`status` onto the preceding assistant message if we want abort visibility (open question, low priority).

Cursor has **no `tool_result` blocks at all** — the harness itself stores inputs only, which happily matches our tool-inputs-only invariant.

### 3b. Claude Code — `*.jsonl` (13 record kinds)

**`assistant`** (1,578 recs):

| Field group | On-disk fields | Disposition → target |
|---|---|---|
| Identity | `uuid`, `parentUuid`, `sessionId`, `type` | KEEP → `messages.message_uid` / `parent_uid` / `session_id` / role |
| Threading/agent | `agentId`, `isSidechain`, `attributionAgent` | KEEP → sessions/subagent linkage |
| Attribution | `attributionSkill`, `attributionMcpServer`, `attributionMcpTool` | KEEP (modest) → `messages.attribution_*` (NULLable) |
| Context | `cwd`, `gitBranch`, `version`, `entrypoint`, `userType` | KEEP `cwd`,`gitBranch`,`version` → sessions; DROP `entrypoint`,`userType` (low value) |
| Time | `timestamp` | KEEP → `messages.ts` |
| Content | `message.content[text].text` | KEEP → text |
| | `message.content[thinking].thinking` + `.signature` | KEEP `thinking`; **DROP `signature`** (opaque crypto blob) |
| | `message.content[tool_use].{id,name,input,caller.type}` | KEEP → `tool_calls` (inputs only) |
| Model | `message.model` | KEEP → `messages.model` (the "model-per-chain" key) |
| Message meta | `message.id`, `message.type`, `message.role` | KEEP `role`; DROP `message.id` (use `uuid`), `message.type` |
| Stop info | `message.stop_reason`, `stop_details`, `stop_sequence` | DROP (not needed for reconstruction/search) |
| **Token usage** | `message.usage.*` (input/output/cache_*, `iterations[]`, `server_tool_use`, `service_tier`, `speed`, `inference_geo`), `requestId`, `message.diagnostics.*` | **DROP** — token/cost is an explicit **v1 exclusion** (roadmap "Future"). Enumerated, not stored. |

**`user`** (909 recs):

| Field | Disposition → target |
|---|---|
| `uuid`, `parentUuid`, `sessionId`, `timestamp`, `type` | KEEP (identity/threading/time) |
| `message.content` (string) **or** `message.content[text].text` | KEEP → text (both shapes occur) |
| `message.content[tool_result].*` (`content`, `is_error`, `tool_use_id`, nested text/tool_reference) | **DROP** — tool **outputs** (inputs-only invariant) |
| `toolUseResult.*` (huge subtree: `stdout`, `stderr`, `file.*`, `structuredPatch[]`, `results[]`, `resolvedModel`, …) | **DROP** — tool **outputs** |
| `agentId`, `isSidechain`, `isMeta` | KEEP `agentId`/`isSidechain`; `isMeta` → flag synthetic/meta user turns (KEEP small) |
| `cwd`, `gitBranch`, `entrypoint`, `userType`, `version` | as assistant (KEEP cwd/gitBranch/version) |
| `promptId`, `promptSource`, `permissionMode`, `queuePriority` | DROP (operational noise) |
| `sourceToolUseID`, `sourceToolAssistantUUID`, `origin.kind` | KEEP — links task-notification user turns back to the spawning tool_use (subagent reconstruction) |

**`system`** (405) — `subtype` (e.g. `turn_duration`), `content`, `level`, `durationMs`, `messageCount`, `pendingBackgroundAgentCount`, + identity/context. Disposition: **DROP** as content (operational logs). Possible exception: `content` carries slash-command invocations (`<command-name>/mcp…`) — low value, drop for v1.

**Session-scoped singletons (fold into `sessions`, drop the record):**

| Record kind | Field kept | → |
|---|---|---|
| `ai-title` | `aiTitle` | `sessions.title` |
| `custom-title` | `customTitle` | `sessions.title` (override) |
| `agent-name` | `agentName` | `sessions.agent_name` |
| `last-prompt` | `lastPrompt`, `leafUuid` | DROP (derivable) |
| `mode` | `mode` | DROP (or `sessions.mode`, low value) |
| `permission-mode` | `permissionMode` | DROP |
| `fork-context-ref` | `parentSessionId`, `parentLastUuid`, `agentId`, `contextLength` | KEEP → subagent/fork linkage on `sessions` |

**Dropped wholesale (not content, not reconstruction):**
- `file-history-snapshot` (400) — editor file-backup bookkeeping (`snapshot.trackedFileBackups.*`). DROP.
- `attachment` (189) — UI/skill-injection deltas (`attachment.addedNames[]`, `deferred_tools_delta`, …). DROP.
- `queue-operation` (56) — prompt queue bookkeeping. DROP.

## 4. Recommended kept subset → draft schema (harness-labeled, one shared set)

> Six table families per the brief: **sessions, messages, tool_calls (inputs-only), plan_documents, embeddings, _sync_state.** Every content row carries a `harness` column. DDL below is an **illustrative sketch for review**, not the locked `0001` text.

```sql
-- one row per conversation; subagents are their own session rows linked to a parent
CREATE TABLE sessions (
    harness            TEXT    NOT NULL,          -- 'cursor' | 'claude'
    session_id         TEXT    NOT NULL,          -- cursor: conv-id from path; claude: sessionId
    project_path       TEXT,                      -- decoded from the encoded project dir
    cwd                TEXT,                      -- claude: cwd; cursor: derived from project_path
    git_branch         TEXT,                      -- claude only
    source_path        TEXT    NOT NULL,          -- absolute path to the .jsonl (provenance + watermark)
    is_subagent        BOOLEAN NOT NULL DEFAULT FALSE,
    parent_session_id  TEXT,                      -- subagent → parent conversation
    agent_id           TEXT,                      -- claude: agentId; cursor: subagent file id
    agent_type         TEXT,                      -- claude: agentType/attributionAgent; cursor: Task.subagent_type
    spawning_tool_use_id TEXT,                    -- claude: meta.json toolUseId; cursor: NULL (structural only)
    agent_name         TEXT,                      -- claude agent-name
    title              TEXT,                      -- claude ai/custom title; cursor NULL (enrich)
    harness_version    TEXT,                      -- claude version; cursor NULL
    started_at         TIMESTAMP,                 -- claude min(ts); cursor NULL/mtime
    ended_at           TIMESTAMP,                 -- claude max(ts); cursor NULL/mtime
    PRIMARY KEY (harness, session_id)
);

-- the message-identity contract + reconstruction keys
CREATE TABLE messages (
    harness        TEXT    NOT NULL,
    session_id     TEXT    NOT NULL,
    message_uid    TEXT    NOT NULL,   -- claude: uuid; cursor: DERIVED det. surrogate (stable across re-ingest)
    parent_uid     TEXT,               -- claude: parentUuid; cursor: prior message_uid (linear chain)
    ordinal        INTEGER NOT NULL,   -- line index in file: ordering key (authoritative for cursor)
    role           TEXT    NOT NULL,   -- 'user' | 'assistant'
    text           TEXT,               -- concatenated text content (stored whole)
    thinking       TEXT,               -- claude thinking blocks; cursor: folded reasoning text
    model          TEXT,               -- claude message.model; cursor NULL/enrich  (model-per-chain)
    ts             TIMESTAMP,          -- claude timestamp; cursor NULL/enrich
    is_meta        BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (harness, session_id, message_uid)
);

-- tool INPUTS only — never outputs
CREATE TABLE tool_calls (
    harness      TEXT NOT NULL,
    session_id   TEXT NOT NULL,
    message_uid  TEXT NOT NULL,        -- FK → messages (the assistant turn that emitted it)
    ordinal      INTEGER NOT NULL,     -- order within the message
    tool_use_id  TEXT,                 -- claude: tool_use.id; cursor: DERIVED surrogate
    tool_name    TEXT NOT NULL,
    tool_input   JSON NOT NULL,        -- stored whole, untruncated
    caller_type  TEXT,                 -- claude: caller.type
    PRIMARY KEY (harness, session_id, message_uid, ordinal)
);

-- forward-declared; populated in Phase 2 (embeddings + search)
CREATE TABLE embeddings (
    harness     TEXT NOT NULL,
    owner_table TEXT NOT NULL,         -- 'messages' | 'tool_calls' | 'plan_documents'
    owner_uid   TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embed_model TEXT NOT NULL,
    vector      FLOAT[384],            -- VSS/HNSW in Phase 2
    PRIMARY KEY (harness, owner_table, owner_uid, chunk_index)
);

-- incremental ingest watermark (per source root)
CREATE TABLE _sync_state (
    harness     TEXT NOT NULL,
    source_root TEXT NOT NULL,
    last_mtime  TIMESTAMP,
    last_path   TEXT,
    updated_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (harness, source_root)
);

-- plan_documents: SEE OPEN QUESTION Q3 — populating source is the weakest-grounded part.
```

## 5. The message-identity contract (the crux)

- **Claude:** `message_uid = uuid` (native, stable); `parent_uid = parentUuid`; `ordinal` = line index (tiebreaker).
- **Cursor:** no native ids. Mint `message_uid` deterministically from `(harness, session_id, ordinal[, role])` so re-ingest of an unchanged file reproduces identical ids (idempotency). `parent_uid` = previous content message's `message_uid` (Cursor is a linear chain; no branching observed). `tool_use_id` similarly synthesized from `(message_uid, ordinal-within-message)`.
- **Reconstruction keys satisfied:** conversation id = `(harness, session_id)`; parent/child = `parent_uid`; ordering = `ordinal`; subagent↔parent = `sessions.parent_session_id` (+ `spawning_tool_use_id` where available); model-per-chain = `messages.model`.

## 6. Open questions for operator review

1. **Token usage / cost (Claude `message.usage.*`)** — recommend **DROP** (v1 explicitly excludes token/cost). It is rich and *only* Claude has it. Confirm dropping, or keep a minimal `usage` stash now to avoid a later migration?
2. **`thinking` content** — recommend **KEEP** the text, **DROP** the `signature` blob. Keep thinking in the same `messages.text` or a separate `thinking` column (sketch uses a separate column)? Note Cursor's "assistant text" blocks are *already* reasoning summaries, so the two harnesses won't be symmetric here.
3. **`plan_documents` source** — this table is named by the brief, but **neither harness emits a distinct "plan document" record** on disk. Candidate sources: (a) `TodoWrite` todo lists (both harnesses), (b) plan-mode assistant messages / Claude `ExitPlanMode`, (c) defer it as forward-declared like `embeddings` until ingest. Need a decision on what populates it.
4. **Cursor model/timestamp enrichment** — confirmed *not* in the transcript and the enrichment DB is on the Windows mount. For the schema this just means `model`/`ts` are NULLable for Cursor. OK to lock that, with enrichment deferred to milestone 3 (ingest)?
5. **Cursor CLI `store.db`** — a separate SQLite format under `~/.cursor/chats/`. Out of scope for this transcript-based enumeration. Confirm it's a milestone-3 ingest concern (or out of v1)?
6. **Non-content Claude records** (`file-history-snapshot`, `attachment`, `system`, `queue-operation`, `mode`, `permission-mode`) — recommend **DROP** entirely. Confirm none are wanted.

## 7. What is NOT done yet (post-review)

Locking the DDL, writing it as `migrations/0001`, the TDD test suite, and committing the durable enumeration record + shared real/pathological fixtures — all wait until the above is reviewed and the kept-subset is approved.
