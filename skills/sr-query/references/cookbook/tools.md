# Tool use rankings

Full `tool_name` rankings with the same activity-window and main-session filters the dashboard uses — without the top-10 cap.

## When to use

- You want the unbounded (or high-LIMIT) tool table, optionally split by harness.
- You want to mirror dashboard `since`/`until` semantics in ad-hoc SQL.

## When not to

- A quick glance at the busiest five tools — the Level-1 inline example in `sr-query/SKILL.md` is enough.
- You need write-vs-read classification — that lives in `stockroom.dashboard.metrics` (`WRITE_TOOLS` / `READ_TOOLS`), not in this recipe.

## SQL

All tools in an activity window (edit the timestamps):

```sql
SELECT t.tool_name,
       count(*) AS calls
FROM tool_calls t
JOIN sessions s
  ON s.harness = t.harness AND s.session_id = t.session_id
WHERE NOT s.is_subagent
  AND COALESCE(s.started_at, s.source_mtime) IS NOT NULL
  AND COALESCE(s.started_at, s.source_mtime) >= TIMESTAMP '2026-01-01'
  AND COALESCE(s.started_at, s.source_mtime) <  TIMESTAMP '2027-01-01'
GROUP BY t.tool_name
ORDER BY calls DESC, t.tool_name
```

By harness:

```sql
SELECT s.harness,
       t.tool_name,
       count(*) AS calls
FROM tool_calls t
JOIN sessions s
  ON s.harness = t.harness AND s.session_id = t.session_id
WHERE NOT s.is_subagent
  AND COALESCE(s.started_at, s.source_mtime) IS NOT NULL
  AND COALESCE(s.started_at, s.source_mtime) >= TIMESTAMP '2026-01-01'
  AND COALESCE(s.started_at, s.source_mtime) <  TIMESTAMP '2027-01-01'
GROUP BY s.harness, t.tool_name
ORDER BY s.harness, calls DESC, t.tool_name
```

## Caveats

- Activity clock is `COALESCE(started_at, source_mtime)` on **sessions**, matching `metrics.ACTIVITY_TIME_SQL` — not `messages.ts`.
- Subagents are excluded (`NOT s.is_subagent`), same as dashboard tool metrics.
- Drop or widen the timestamp predicates for an all-time table; keep the subagent filter unless you intentionally want subagent noise.

## Verified against

`stockroom.dashboard.metrics.tools` / `ACTIVITY_TIME_SQL`. Drift trigger: `skills/sr-search/src/stockroom/dashboard/metrics.py`.
