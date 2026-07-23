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

The fixtures are laid out as two faithful **harness roots** — `cursor/` mirrors
`~/.cursor/projects` and `claude/` mirrors `~/.claude/projects` — so the ingest
discovery/parse/orchestrator tests scan them exactly as the live ingest scans
the operator's real history. The encoded project-dir name is the session's
**`project_id`**, carried *verbatim* (Cursor drops the leading separator, e.g.
`home-user-project`; Claude keeps it as a leading dash, e.g. `-home-user-project`).
The real **`cwd`** is recovered separately — from the records for Claude, and by
re-encode-and-match over in-band paths for Cursor — and is honestly `NULL` when
no evidence is present (never the old lossy decode).

```
transcripts/
  cursor/                                     root == ~/.cursor/projects
    home-user-project/                          project_id "home-user-project"
      agent-transcripts/
        simple-conversation/simple-conversation.jsonl   conv dir holds <conv>.jsonl;
                                                         user -> assistant(text+tool) -> assistant; ends turn_ended
                                                         (relative paths only -> cwd resolves to NULL)
        pathological-many-tools/...jsonl        one assistant turn emitting many tool_use blocks; empty text block
        pathological-turn-ended-error/...jsonl  a turn_ended abort with status:"error"
        00000000-0000-4000-8000-000000000001/
          00000000-0000-4000-8000-000000000001.jsonl   parent: a Task tool_use (no child id — structural link only)
          subagents/
            00000000-0000-4000-8000-0000000000a1.jsonl  child: bare message list under the parent's subagents/ dir
    home-user-lite-rpg/                         project_id "home-user-lite-rpg"
      agent-transcripts/
        recover-inband/recover-inband.jsonl     in-band /home/user/lite-rpg/src/main.py -> cwd recovers to
                                                /home/user/lite-rpg (hyphenated leaf the naive decode would mangle)
    home-user-cursor-rules/                     project_id "home-user-cursor-rules"
      agent-transcripts/
        ambiguous-nopath/ambiguous-nopath.jsonl no in-band absolute path -> honest cwd = NULL
  claude/                                     root == ~/.claude/projects
    -home-user-project/                         project_id "-home-user-project"; record cwd -> /home/user/project
      simple-conversation.jsonl                 mode singleton; user; assistant(thinking+text+tool_use+usage+model);
                                                user tool_result (DROP — inputs only); assistant(end_turn); ai-title
      pathological-multi-model.jsonl            one conversation whose assistant turns use two different models
      pathological-huge-tool-input.jsonl        an assistant turn with a large tool_input (no-truncation case)
      pathological-user-content-shapes.jsonl    user content as a list of text blocks (KEPT, joined) vs a list
                                                of only tool_result (DROPPED); parent resolves past the drop
      robustness-record-types.jsonl             real-log diversity: mode/system/attachment/file-history-snapshot/
                                                permission-mode/last-prompt/queue-operation (all IGNORED) interleaved
                                                with a real user->assistant turn; custom-title + agent-name (FOLDED)
      22222222-2222-4222-8222-222222222222.jsonl        parent: assistant Task tool_use id toolu_task1
      22222222-2222-4222-8222-222222222222/
        subagents/
          agent-aaa111.jsonl        child: isSidechain=true, agentId, agent-name record; includes a tool_result (DROP)
          agent-aaa111.meta.json    explicit parent link {agentType, description, toolUseId}; toolUseId -> parent tool_use.id
```

### Synthetic enrichment DB

The optional Cursor `ai-code-tracking.db` model-enrichment source is resolved
at runtime by walking all readable conventional/`ai-tracking` and WSL
Windows-mount candidates (plus optional XDG `ai_tracking_dbs` pins), unless
`STOCKROOM_AI_TRACKING_DB` forces a single DB. Its happy path is exercised
against a synthetic, clean-room sqlite DB built at test time by the
`ai_tracking_db` pytest fixture (in `tests/conftest.py`) from documented SQL —
reviewable, with no opaque binary committed. It mirrors the current Cursor
schema subset ingest reads (`ai_code_hashes`, `conversation_summaries`) keyed
by Cursor conversation id, overlapping the committed Cursor transcript
fixtures so the orchestrator can apply enrichment to real rows.

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
- **record-type diversity** (`claude/robustness-record-types`) — real logs
  interleave many record types the m1 fixtures omitted; the parser folds
  metadata records (`custom-title`→title, `agent-name`→agent_name) and ignores
  the rest (`system`, `attachment`, `file-history-snapshot`, `permission-mode`,
  `last-prompt`, `queue-operation`) without crashing or emitting rows.
- **cwd recovery** (`cursor/home-user-lite-rpg/recover-inband`) — Cursor carries
  no `cwd`; the real path is recovered by re-encode-and-match over an in-band
  absolute path, correctly handling a hyphenated leaf (`/home/user/lite-rpg`,
  not the naive `/home/user/lite/rpg`).
- **honest NULL cwd** (`cursor/home-user-cursor-rules/ambiguous-nopath`) — when
  no in-band path re-encodes to the slug, `cwd` stays `NULL`; the lossy old
  decode is never used to fabricate one.
