---
name: sr-search
description: Search your local warehouse of agentic-coding history — the friendly default entrypoint. Reach for this when you are unsure whether the question is an exact/structured lookup (sr-query) or meaning-based recall (sr-semantic), or when it needs both — it routes the question, runs the right surface(s), and synthesizes one answer.
enable-model-invocation: true
---

# sr-search

`sr-search` answers a question about your captured Cursor + Claude Code history by judging what kind of lookup it is, delegating to the right sibling skill(s), and synthesizing the results into one answer.

## Route the question

Classify the ask, then **follow the chosen sibling skill** for how to run the search. The siblings live beside this file — `../sr-query/SKILL.md`, `../sr-semantic/SKILL.md` — read one directly if your harness doesn't surface it by name.

| The ask | Route |
|---------|-------|
| Exact or structured — fields you can name: ids, filters, counts, `GROUP BY`, joins ("how many sessions per harness?") | `sr-query` alone |
| Meaning-based — content you can describe but not name exactly ("where did we debug the warehouse deadlock?") | `sr-semantic` alone |
| Known id in hand ("show me message `<id>` in full") | `sr-query` alone |
| Per-session / conversation token rollups or spend ("which chats used the most tokens?") | `sr-query` alone — use VIEW `session_token_usage` (see `../sr-query/SKILL.md`; more rollups in its [cookbook](../sr-query/references/cookbook/index.md)) |
| Full skill-use or tool-use tables beyond dashboard top-N | `sr-query` alone — [cookbook](../sr-query/references/cookbook/index.md) |
| Broad or ambiguous — both a nameable shape and a describable concept ("find everything about REUSE licensing") | Both surfaces, then synthesize |

If the routed surface comes back empty or thin, try the other surface before concluding the content isn't there.

## Synthesize and present

- Default grain: answer in prose, citing the supporting hits (session/message ids) as evidence.
- List-shaped asks ("show me the sessions about X"): present one merged list, ordered by your relevance judgement.
- Dedup across surfaces by `message_id` / `(harness, session_id)`. A hit found by both routes is a strong relevance signal — surface it prominently.
- Never blend or compare scores across surfaces: semantic similarity is relative within one query, and SQL rows carry no score.
- Scan at the siblings' default detail; when the answer needs a whole message, fetch it via the full-text handoff the siblings document.
- You are the operator, not the display: answer the user in natural language, and hand raw output only when they ask for it.

## Engine home

This directory also hosts the shared stockroom engine (`src/stockroom/`) that every `sr-*` skill invokes as `stockroom <subcommand>` — developers, see the repo README and `memory-bank/systemPatterns.md`. To understand *why* the system's contracts look the way they do, read the shared system model: [`references/system-model.md`](references/system-model.md).
