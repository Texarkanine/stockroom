# Skill Use (Claude)

**When:** Claude skill × invoker counts from warehouse SQL (user `<command-name>` + agent `Skill` tool).

```sql
WITH activity AS (
  SELECT s.harness, s.session_id
  FROM sessions s
  WHERE s.harness = 'claude'
    AND NOT s.is_subagent
    AND COALESCE(s.started_at, s.source_mtime) IS NOT NULL
),
user_skills AS (
  SELECT
    regexp_extract(m.text, '<command-name>\s*/([^<\s]+)\s*</command-name>', 1) AS skill,
    'user' AS invoker
  FROM messages m
  JOIN activity a
    ON a.harness = m.harness AND a.session_id = m.session_id
  WHERE m.role = 'user'
    AND m.text LIKE '%<command-name>/%'
    AND NOT starts_with(ltrim(m.text), 'Base directory for this skill:')
),
agent_skills AS (
  SELECT
    trim(json_extract_string(t.tool_input, '$.skill')) AS skill,
    'agent' AS invoker
  FROM tool_calls t
  JOIN activity a
    ON a.harness = t.harness AND a.session_id = t.session_id
  WHERE t.tool_name = 'Skill'
),
events AS (
  SELECT skill, invoker FROM user_skills
  WHERE skill <> ''
    AND skill NOT IN (
      'add-dir',
      'agents',
      'bashes',
      'bug',
      'clear',
      'color',
      'compact',
      'config',
      'context',
      'cost',
      'desktop',
      'diff',
      'effort',
      'exit',
      'export',
      'extra-usage',
      'fast',
      'files',
      'help',
      'hooks',
      'ide',
      'init',
      'insights',
      'install-github-app',
      'keybindings',
      'login',
      'logout',
      'mcp',
      'memory',
      'migrate-installer',
      'mobile',
      'model',
      'output-style',
      'permissions',
      'plan',
      'plugin',
      'privacy-settings',
      'release-notes',
      'reload-plugins',
      'rename',
      'review',
      'rewind',
      'security-review',
      'stats',
      'status',
      'terminal-setup',
      'theme',
      'think',
      'todos',
      'upgrade',
      'usage',
      'vim',
      'voice'
    )
  UNION ALL
  SELECT skill, invoker FROM agent_skills
  WHERE skill IS NOT NULL AND skill <> ''
)
SELECT skill, invoker, count(*) AS uses
FROM events
GROUP BY skill, invoker
ORDER BY uses DESC, skill, invoker
```

Only the first `<command-name>` match per message is taken. Builtin `NOT IN` list tracks `_CLAUDE_BUILTIN_COMMANDS` in `skill_usage.py` (test-pinned).
