# Progress

## 2026-06-22 — Brainstorm drafted

- Explored the three reference repos and confirmed the uv lockfile/supply-chain story (a committed lockfile + `--frozen` pins and hash-verifies deps; `uvx`/loose-PEP723 does not).
- Ran two operator question rounds; settled decisions D1–D18 and identified Open Items O1–O9 (see `planning/brainstorm/README.md`).
- Wrote `planning/brainstorm/`: `README.md`, `product.md`, `tech.md`, `roadmap.md`, `implementation-details.md`.
- Seeded `memory-bank/active/` (projectbrief, activeContext, tasks, progress) so the planning task is resumable from a fresh context window.

## 2026-06-22 — Lossless capture folded in

- Operator added a core principle: **never truncate** prompts/responses/tool I/O. The references' truncation is what reduces them to "fun toys."
- Verified empirically via `cw-query`: `cursor-warehouse` hard-caps `text_content`/`user_query` at 2000 chars and `tool_input` at 500, and stores no tool outputs; ~17% of messages were truncated. Source JSONL true max single field ~202 KB. DuckDB `VARCHAR` is effectively unbounded (4 GB), so untruncated storage is free.
- Added D19 (lossless capture + tool outputs + verbatim raw layer) and D20 (schema designed against both Cursor + Claude formats). Resolved O2 (both manifests ship); added O10–O12.
- Updated `product.md`, `tech.md`, `implementation-details.md`, `roadmap.md`, and `README.md`.

## 2026-06-22 — Capture model refined (ETL, not mirroring)

- Operator reversed two earlier additions: **no verbatim raw layer** (ingest is ETL into our schema, not a byte-for-byte mirror — the source has fields we don't care about) and **no tool outputs** (inputs only; outputs are high-bulk/low-recall). Resolved O10 → no.
- Clarified the principle precisely: **no truncation at rest** of kept content, but **read-time truncation is a desirable feature** — the `sr-search` entrypoint should reason about an appropriate output-truncation level so a 200 KB field never floods the agent's context window. "Lossless" reframed as **"faithful."**
- Captured the operator's schema-design method (point an agent at each harness's logs, enumerate fields, pick what to keep) and the **core field set** (D22): timestamp, full content, role/type, model-per-chain, subagent↔parent linkage, tool inputs, optional thinking, harness plan docs.
- Added **D21 (conversation reconstruction/linkage is first-class)** — finding a plan doc is far more valuable when you can see which conversation it belongs to. Added O13 (read-time truncation), O14 (plan-doc artifacts per harness), O15 (thinking capture).
- Updated all five brainstorm files (`product.md`, `tech.md`, `implementation-details.md`, `roadmap.md`, `README.md`) and this memory bank — including scrubbing the tool-output / raw-layer language from `roadmap.md` Phases 0–1.

## 2026-06-22 — Open items resolved; brainstorm finalized + committed

- Operator set **v1 scope = both Cursor and Claude Code** (O12 resolved). Updated D2 and every downstream reference (product / tech / roadmap / impl-details).
- Resolved all remaining open items by reasoned default: O1 `~/.stockroom/` (XDG-aware), O3 model/labeling-only, O4 forward-only, O6 stdlib server + vendored assets, O7 subagents yes, O8 no Windows-native scheduling, O11 inline storage (isolation deferred). Restructured the README Open Items into **Resolved** + **Still Open**.
- **O9 (torch) is the lone unresolved item** — flagged honestly as an empirical `uv` spike that can't be settled by fiat. It's the first task of the Tech Brief and does not block the PB.
- Captured the clean-room nuance for Claude Code ingest: parse the *harness's* native on-disk format independently — never reuse `claude-warehouse` code or schema DDL.
- Committed `planning/` + `memory-bank/`. Next: author the Product Brief in a fresh context window.

## Status

Brainstorm finalized and committed; it is the locked source of truth. Only **O9 (torch spike)** remains, deferred to the Tech Brief. Next deliverable: the **Product Brief**. No product code written.

## Notable Decisions Reversed During Refinement

- Dashboard vs recap: flipped to **dashboard in v1, recap deferred** (recap reconceived as dashboard-metrics-over-time).
- Migration trigger: moved from session-start **hook** to a **lazy gate** inside skills + the nightly job; the hook now only launches the dashboard.
- Torch: hardened to "**never lock torch across platforms**; lock everything else" (was "GPU via user index").
- Harness scope: from **Cursor-only** toward **both Cursor + Claude Code in v1** + ship both manifests (to avoid single-harness schema bias). O12 later resolved → both.
