# Cursor skill use

**When:** Cursor skill × invoker counts from warehouse SQL (user `Skill Name:` attach lines + agent `Read` of `…/SKILL.md`).

```sql
WITH activity AS (
  SELECT s.harness, s.session_id
  FROM sessions s
  WHERE s.harness = 'cursor'
    AND NOT s.is_subagent
    AND COALESCE(s.started_at, s.source_mtime) IS NOT NULL
),
user_skills AS (
  SELECT
    unnest(regexp_extract_all(m.text, 'Skill Name:\s*(\S+)', 1)) AS skill,
    'user' AS invoker
  FROM messages m
  JOIN activity a
    ON a.harness = m.harness AND a.session_id = m.session_id
  WHERE m.role = 'user'
    AND m.text LIKE '%<manually_attached_skills>%'
),
agent_skills AS (
  SELECT
    regexp_extract(
      replace(
        coalesce(
          json_extract_string(t.tool_input, '$.path'),
          json_extract_string(t.tool_input, '$.file_path'),
          ''
        ),
        chr(92),
        '/'
      ),
      '.*/([^/]+)/SKILL\.md$',
      1
    ) AS skill,
    'agent' AS invoker
  FROM tool_calls t
  JOIN activity a
    ON a.harness = t.harness AND a.session_id = t.session_id
  WHERE t.tool_name = 'Read'
    AND coalesce(
      json_extract_string(t.tool_input, '$.path'),
      json_extract_string(t.tool_input, '$.file_path')
    ) LIKE '%/SKILL.md'
),
events AS (
  SELECT skill, invoker FROM user_skills WHERE skill <> ''
  UNION ALL
  SELECT skill, invoker FROM agent_skills WHERE skill <> ''
)
SELECT skill, invoker, count(*) AS uses
FROM events
GROUP BY skill, invoker
ORDER BY uses DESC, skill, invoker
```

Agent skill name is the parent directory of `SKILL.md`. User regex is slightly looser than the extractor's line-anchored `^Skill Name:`.
