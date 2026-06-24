# Transcript Fixtures

Durable, committed sample transcripts in the **native on-disk formats** of the
two harnesses stockroom ingests: Cursor (IDE agent) and Claude Code. They exist
so the milestone-3 ingest/ETL work — and any future-harness onboarding — has a
stable, reviewable corpus of real-shaped records to parse against, including the
pathological shapes that a naive parser gets wrong.

## Scope

- **Not parsed by milestone-1 tests.** The schema-contract suite
  (`tests/test_schema_0001.py`) inserts rows directly; it never reads these
  files. They are deliberately landed now as artifacts for later phases.
- **Faithful to record *shape*, synthetic in *content*.** Every record
  reproduces the exact keys/structure observed in the harnesses' real on-disk
  logs (enumerated in `memory-bank/.../creative-schema-enumeration.md`), but all
  human/content fields are rewritten to a small synthetic "add a hello function"
  scenario. See Scrubbing below.

## Scrubbing Policy

Because these are committed to a public repo, no real transcript bytes are
copied. Each fixture was hand-authored from the *structure* of real records
with every potentially-sensitive value replaced:

- **Identifiers** (`sessionId`, `uuid`, `parentUuid`, tool-use ids, agent ids)
  → deterministic synthetic values.
- **Paths** (`cwd`, `file_path`, project dirs) → `/home/user/project`.
- **Content** (prompts, responses, tool inputs, tool results) → synthetic toy
  text. Claude `thinking.signature` blobs → the literal `"SCRUBBED"`.
- **No tokens, keys, emails, or machine-specific values** appear anywhere.

The token-usage *numbers* are illustrative (small, plausible), not real.

## Layout

```
transcripts/
  cursor/                         bare role/message JSONL (metadata-sparse)
    simple-conversation.jsonl       user -> assistant(text+tool) -> assistant; ends turn_ended
    pathological-turn-ended-error.jsonl   a turn_ended abort with status:"error"
    pathological-many-tools.jsonl   one assistant turn emitting many tool_use blocks; empty text block
    with-subagent/
      00000000-0000-4000-8000-000000000001.jsonl   parent: a Task tool_use (no child id — structural link only)
      subagents/
        00000000-0000-4000-8000-0000000000a1.jsonl  child: bare message list under the parent's subagents/ dir
  claude/                         self-describing JSONL (rich per-record metadata)
    simple-conversation.jsonl       mode singleton; user; assistant(thinking+text+tool_use+usage+model);
                                    user tool_result (DROP — inputs only); assistant(end_turn); ai-title
    pathological-multi-model.jsonl  one conversation whose assistant turns use two different models
    pathological-huge-tool-input.jsonl  an assistant turn with a large tool_input (no-truncation case)
    with-subagent/
      22222222-2222-4222-8222-222222222222.jsonl   parent: assistant Task tool_use id toolu_task1
      subagents/
        agent-aaa111.jsonl          child: isSidechain=true, agentId; includes a tool_result (DROP)
        agent-aaa111.meta.json      explicit parent link: toolUseId -> parent's tool_use.id
```

## What Each Pathological Case Guards

- **`cursor/.../many-tools` + `claude` thinking** — a turn is
  `[thinking?, text?, tool_use*]`; tools are children of a turn, not peers.
- **empty text block** (`cursor/simple`, `many-tools`) — a `text` block may be
  `""`; ingest must keep it, not drop the turn.
- **`turn-ended-error`** — Cursor's `turn_ended` marker is not content; an
  `error`/`status` may need surfacing onto the preceding turn.
- **Claude `tool_result` / `toolUseResult`** (`claude/simple`, subagent child)
  — tool **outputs**; stockroom stores inputs only, so these must be dropped.
- **multi-model** — a single conversation can span models (Claude per-message
  grain; the session-grain `models` LIST is for Cursor).
- **huge tool_input** — kept content is stored whole, never truncated at rest.
- **subagents** — Claude links child→parent explicitly via
  `meta.json.toolUseId`; Cursor links only structurally (child file living in
  the parent's `subagents/` directory).
