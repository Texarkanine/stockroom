## Token usage (VIEW)

**When:** top-N sessions, by-harness totals, or a day rollup from `session_token_usage` (prefer the VIEW over hand-rolled `SUM` on `messages`).

### Top sessions

```sql
SELECT harness, session_id, input_tokens_total, output_tokens_total, token_grain
FROM session_token_usage
ORDER BY input_tokens_total DESC NULLS LAST
LIMIT 20
```

### By harness

```sql
SELECT harness,
       sum(input_tokens_total) AS input_tokens,
       sum(output_tokens_total) AS output_tokens,
       count(*) AS sessions
FROM session_token_usage
GROUP BY harness
ORDER BY input_tokens DESC NULLS LAST
```

### By day

Join sessions for activity time (`COALESCE(started_at, source_mtime)`):

```sql
SELECT date_trunc('day', COALESCE(s.started_at, s.source_mtime)) AS day,
       s.harness,
       sum(t.input_tokens_total) AS input_tokens,
       sum(t.output_tokens_total) AS output_tokens
FROM session_token_usage t
JOIN sessions s
  ON s.harness = t.harness AND s.session_id = t.session_id
WHERE COALESCE(s.started_at, s.source_mtime) IS NOT NULL
GROUP BY 1, 2
ORDER BY 1 DESC, 2
```

`*_total` is `COALESCE(native, from_messages)` — do not also `SUM` message tokens on top. `token_grain` is `'session'` | `'message'` | `'none'`.
