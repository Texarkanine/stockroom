# Cross-harness Warehouse — builder spec

The mock (`Cross-harness Warehouse.dc.html`) is the visual + behavioral source of truth.
This note captures the parts a static screenshot can't: the cross-harness rules and the
JSON each endpoint must return. Backend is Python, no external deps — keep it KISS.

## Core rules

1. **Harness set is open.** Never hard-code the list. Enumerate `SELECT DISTINCT harness`
   at query time. New harnesses light up automatically in the selector.
2. **Signature colors are positional**, assigned client-side. Sort the active harnesses
   deterministically (alphabetical is fine), then map index → palette:
   `['#6366f1','#10b981','#f59e0b','#f43f5e','#06b6d4','#8b5cf6','#ec4899','#84cc16']`.
   The server returns raw per-harness data keyed by harness name; it does NOT assign colors.
3. **Aggregate vs Compare is a client concern.** The server always returns data broken out
   **per harness**. Aggregate mode sums/blends client-side (single series); Compare mode
   renders one series per harness. This keeps every endpoint mode-agnostic.
   - Exception worth noting: `projects` cannot be summed across harnesses (a project can be
     touched by several). For the "All / multi-select" total, return a distinct project count
     server-side (see `/api/overview`).
4. **Selection is a client filter.** Endpoints accept `?harness=cursor&harness=claude`
   (repeatable) or omit for all. Prefer filtering server-side for large stores.
5. **Averages don't sum.** `avg_msgs`, first-prompt averages, etc. must be recomputed over
   the selected set, not averaged-of-averages. Simplest: return the numerator + denominator
   per harness and let the client (or a server rollup) divide.

## Endpoints & shapes

All accept optional repeated `?harness=` filters. Times are ISO-8601.

### `GET /api/overview`
```json
{
  "last_sync": "2026-07-09T03:00:30",
  "per_harness": {
    "cursor": {"sessions":211,"messages":8024,"projects":12,
               "prev_sessions":68,"prev_messages":1860,"prev_projects":9},
    "claude": {"sessions":540,"messages":19180,"projects":29, "...":  "..."}
  },
  "distinct_projects": 41   // for the aggregate Projects card; != sum(projects)
}
```
Deltas (`+118% vs prev 30d`) are computed client-side from cur/prev.

### `GET /api/trends`  (Daily Activity + Write/Read)
```json
{
  "daily":  { "days": ["2026-06-26", "..."],
              "sessions": { "cursor":[4,3,...], "claude":[12,9,...] } },
  "weekly": { "weeks": ["2026-05-11", "..."],
              "writes": { "cursor":[...], "claude":[...] },
              "reads":  { "cursor":[...], "claude":[...] } }
}
```
Write/Read blends across the selection in both modes (it's a ratio, not a per-harness
breakout) — writes = tool_calls where tool_name in the write set, reads in the read set.

### `GET /api/projects`
```json
{ "projects": ["stockroom","lite-rpg","..."],
  "sessions": { "cursor":[35,90,...], "claude":[80,6,...] } }
```
Top N projects by total sessions; each harness supplies its count per project.

### `GET /api/tools`
```json
{ "tools": ["Read","Shell","StrReplace","..."],
  "calls": { "cursor":[520,340,...], "claude":[1400,820,...] } }
```
From `tool_calls.tool_name`. Aggregate mode → donut of column sums; Compare → stacked bar.

### `GET /api/models`  (new metric)
```json
{ "models": ["claude-fable-5","claude-sonnet-5","gpt-5","..."],
  "sessions": { "cursor":[40,60,90,...], "claude":[340,150,0,...] } }
```
**Grain caveat — read the schema.** Model lives at different grains per harness:
`messages.model` (Claude, per message) vs `sessions.models VARCHAR[]` (Cursor, per
conversation). Pick ONE canonical grain and document it. Recommendation: **session grain** —
a session "used" model M if M appears in its messages (Claude) or its `models[]` array
(Cursor). That makes the count directly comparable across harnesses. Aggregate sums the
columns; Compare stacks by harness.

### `GET /api/efficiency`
```json
{ "buckets": ["abandoned","short","medium","long"],
  "sessions": { "cursor":[3,60,80,68], "claude":[8,120,180,232] },
  "first_prompt": { "labels":["short","medium","detailed"],
                    "avg_msgs": { "cursor":[12,29,36], "claude":[15,33,41] },
                    "n": { "cursor":[...], "claude":[...] } }  // counts, for weighted agg
}
```
Bucket a session by message count (tune thresholds). `first_prompt` buckets by the length
of the session's ordinal-0 user message; return `n` so averages can be re-weighted.

### `GET /api/sessions?limit=50`
```json
[ {"started":"2026-07-09 02:44","harness":"claude","project_name":"stockroom",
   "msgs":84,"model":"claude-fable-5","prompt":"<manually_attached_skills> ..."} ]
```
Include `harness` so the client can draw the colored dot and filter.

### `GET /api/wrapped`
All-time rollup across all harnesses. Same fields as today, plus a `busiest_harness`
`{name, pct}`. Not affected by the selector.

## Notes for later phases
- Tokens/cost cards were intentionally left out: Cursor has no per-message token data
  (`messages.input_tokens` is NULL), so a cross-harness token card would be misleading.
  If added, gate it to harnesses that actually report tokens and label the gap.
- Subagent metrics (`is_subagent`, `parent_session_id`) and git-branch activity (Claude
  only) are good Compare-mode-only additions.
