# Cursor skill use (SQL escape hatch)

Approximate Cursor skill × invoker counts from warehouse SQL. Dashboard extractors remain the product definition for charts.

## When to use

- You need a full skill table (beyond dashboard top-N) and accept regex/path heuristics.
- You are debugging candidate rows that feed `extract_cursor`.

## When not to

- You need chart-faithful skill identity — use the dashboard / `stockroom.dashboard.skill_usage.extract_cursor`.
- Claude sessions — use the `skills-claude.md` recipe in this cookbook.

## SQL

User invokers (`Skill Name:` lines inside `<manually_attached_skills>`) + agent invokers (`Read` of a path ending in `SKILL.md` → parent directory name):

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

## Caveats

- Product truth for skill charts is `stockroom.dashboard.skill_usage` (Python), not this SQL.
- Agent skill name is the **parent directory** of `SKILL.md` (case-sensitive suffix), matching `_skill_from_read_path`.
- User regex is slightly looser than the extractor's line-anchored `^Skill Name:` (MULTILINE); false positives outside attach blocks are possible if the phrase appears elsewhere in a message that also contains the attach marker.
- Residual gaps vs Python: malformed JSON `tool_input`, unusual path shapes, and harness-specific attach formats the extractor handles in code.

## Verified against

`stockroom.dashboard.skill_usage.extract_cursor`. Drift trigger: `skills/sr-search/src/stockroom/dashboard/skill_usage.py` and `tests/test_dashboard_skill_usage.py`.
