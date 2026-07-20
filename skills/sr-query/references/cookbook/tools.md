# Tool use rankings

**When:** full `tool_name` table (beyond dashboard top-10), optionally by harness, with the same activity window as dashboard metrics.

## All tools in a window

Edit the timestamps (or drop them for all-time):

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

## By harness

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

Activity clock is session `COALESCE(started_at, source_mtime)`, not `messages.ts`. Subagents stay excluded unless you want that noise.
