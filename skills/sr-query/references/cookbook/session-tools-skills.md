# Per-session tools & skills

**When:** tool-name and skill distribution for one conversation (dashboard session composition charts).

Replace the harness / session id literals.

## Tools for one session

```sql
SELECT t.tool_name,
       count(*) AS calls
FROM tool_calls t
WHERE t.harness = 'cursor'
  AND t.session_id = 'YOUR_SESSION_ID'
GROUP BY t.tool_name
ORDER BY calls DESC, t.tool_name
```

## Skills for one Claude session

Agent `Skill` tool + user `<command-name>` (same extractors as the dashboard; builtins omitted here for brevity — see [skills-claude.md](skills-claude.md) for the full denylist):

```sql
WITH agent_skills AS (
  SELECT trim(json_extract_string(t.tool_input, '$.skill')) AS skill,
         'agent' AS invoker
  FROM tool_calls t
  WHERE t.harness = 'claude'
    AND t.session_id = 'YOUR_SESSION_ID'
    AND t.tool_name = 'Skill'
),
user_skills AS (
  SELECT regexp_extract(m.text, '<command-name>\s*/([^<\s]+)\s*</command-name>', 1) AS skill,
         'user' AS invoker
  FROM messages m
  WHERE m.harness = 'claude'
    AND m.session_id = 'YOUR_SESSION_ID'
    AND m.role = 'user'
    AND m.text LIKE '%<command-name>/%'
),
events AS (
  SELECT skill, invoker FROM agent_skills WHERE skill <> ''
  UNION ALL
  SELECT skill, invoker FROM user_skills WHERE skill <> ''
)
SELECT skill, invoker, count(*) AS uses
FROM events
GROUP BY skill, invoker
ORDER BY uses DESC, skill, invoker
```

For Cursor skill patterns (Read of `…/SKILL.md` + manually attached skills), start from [skills-cursor.md](skills-cursor.md) and add `AND t.session_id = '…'` / `AND m.session_id = '…'` to the joins.
