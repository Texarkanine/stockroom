# Token usage (VIEW)

Per-conversation token rollups without hand-rolled `SUM` on `messages`.

## When to use

- You need top-N sessions, by-harness totals, or a simple day rollup of reported tokens.
- Prefer VIEW `session_token_usage` over re-deriving `*_from_messages` / `*_native` / `*_total`.

## When not to

- You need vendor-invoice truth — these are warehouse rollups of reported fields, not billing.
- You need meaning-based recall — use `sr-semantic`.

## SQL

Top sessions by input tokens:

```sql
SELECT harness, session_id, input_tokens_total, output_tokens_total, token_grain
FROM session_token_usage
ORDER BY input_tokens_total DESC NULLS LAST
LIMIT 20
```

Totals by harness:

```sql
SELECT harness,
       sum(input_tokens_total) AS input_tokens,
       sum(output_tokens_total) AS output_tokens,
       count(*) AS sessions
FROM session_token_usage
GROUP BY harness
ORDER BY input_tokens DESC NULLS LAST
```

Day rollup (activity from the VIEW's session clock — join sessions for `COALESCE(started_at, source_mtime)`):

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

## Caveats

- `*_total` is `COALESCE(native, from_messages)` — do **not** also `SUM` message tokens on top.
- `token_grain` is `'session'` | `'message'` | `'none'`; many Cursor rows are `'none'`.
- Filter `NULLS LAST` when ranking — zero-token / unreported sessions sort honestly.

## Verified against

Migration head including VIEW `session_token_usage` (0007). Drift trigger: `skills/sr-search/src/stockroom/warehouse/migrations/` VIEW definition + `sr-query/SKILL.md` worked example.
