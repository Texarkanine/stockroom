# Task: `sr-query` skill

* Task ID: `p2-embeddings-search` (sub-run m4)
* Complexity: Level 2
* Type: Simple enhancement (skill authoring — prose wrapper over an existing engine surface)

Author `skills/sr-query/SKILL.md`: the safe, LLM-ergonomic wrapper around the already-built read-only SQL surface (`python -m stockroom.query`). The skill is the **single home** for operational knowledge about *that* surface — when to reach for raw SQL, how to invoke it through the torch-safe / plugin-root-resolution contract, how to drive the `--format` / `--detail` flags landed in m3/m3.5, and the guardrails that keep an LLM from blowing out its context window or burning failed tool calls. Per the project invariant, **prompt-skill behavior is verified artisanally by the operator**; the TDD rule binds only Python, and this sub-run writes **no Python** (decision below), so the automated gate is "`make ci` stays green + `make reuse` covers the new file."

## Scope Decisions (resolving milestone open questions)

These were flagged in `milestones.md` as "resolve when authoring the first wrapper skill":

- **Prose-only — no helper `scripts/` this sub-run.** The surface is a single `python -m stockroom.query` call behind the already-documented resolution preamble; a bash resolver would re-introduce the same plugin-root resolution problem it tries to hide, and an LLM resolving `APP_DIR` *once* then reusing it is cleaner than shelling a script from an unknown cwd. Adding Python would also drag in the TDD obligation for no real gain. If `sr-semantic`/`sr-search` later want a shared resolver, that is their decision. **Where helper scripts live (when needed): `skills/<skill>/scripts/`** — recorded for the future, not exercised here.
- **Front-matter: `enable-model-invocation: true`.** Unlike the `sr-search` skeleton (`false`, no behavior yet), `sr-query` is a live, model-invocable skill. `name: sr-query`; `license: "Multiple — see LICENSES/ and REUSE.toml"` (mirrors `sr-search`).
- **Invocation contract is inlined**, copied from the established `sr-search` SKILL.md precedent + `systemPatterns.md` (plugin-root resolution with `find -L` fallback, then torch-safe `uv run --project "$APP_DIR" --no-sync python -m stockroom.query …`).

## Test Plan (TDD)

This deliverable is **prose** (`SKILL.md`). The project invariant (`milestones.md`, `creative-search-surface-architecture.md`) explicitly carves prompt-skills out of `pytest`: their behavior is **verified artisanally by the operator**, while the TDD rule binds Python. No Python is written this sub-run, so there are no new unit tests; the automated gates that must stay green are the licensing lint and the unchanged Python suite.

### Behaviors to Verify (artisanal — operator exercises the skill)

- **Routing in**: agent has a task answerable by exact/structured lookup (a known id, a `WHERE` filter, a `COUNT`/`GROUP BY`) → reaches for `sr-query` and writes a `SELECT`, default `--format tsv --detail snippet` → bounded, parseable stdout.
- **Elision → full**: output shows `…(+N)` on a field the agent actually needs → re-runs with `--detail full` (or a narrower `SELECT` of just that column + a `LIMIT`) → gets the whole field.
- **Cheap scan**: agent scanning many candidate rows before picking one → uses `--detail compact` to scan, then re-fetches the chosen row at `full`.
- **Human / structured on request**: user asks for a copy-paste command or human-readable output → skill offers `--format table`; asks for structured → `--format json`.
- **Context-blowout guardrail**: agent does NOT `SELECT *` wide text columns at `--detail full` across many rows; prefers explicit narrow columns + `LIMIT`.
- **Read-only guardrail**: agent does NOT attempt `INSERT`/`UPDATE`/`DELETE` (DuckDB rejects → `query failed: …`, exit 1); the skill tells it the surface is read-only and not to retry writes.
- **Absent warehouse**: warehouse missing → `error: no warehouse found at … — run python -m stockroom.ingest first` (exit 1) → agent relays the hint to the user instead of looping.
- **Invalid SQL**: bad SQL → `query failed: …` (exit 1) → agent fixes the statement, does not thrash.
- **Empty query**: empty/whitespace SQL → `error: empty query …` (exit 2).
- **Schema orientation**: agent can write valid SQL on the first try because the skill names the queryable tables/columns (no schema trial-and-error).

### Test Infrastructure

- Framework: `pytest`, configured in `skills/sr-search/pyproject.toml`; run via `make test` / full gate `make ci` from repo root.
- Licensing: `make reuse` (REUSE/SPDX lint) — the new `skills/sr-query/SKILL.md` is covered by the existing `skills/**` → PPL-S glob in `REUSE.toml`; **no `REUSE.toml` edit needed**, but `make reuse` must confirm the file resolves to a license.
- Conventions: tests live in `skills/sr-search/tests/test_<module>.py`. **Not applicable here** — no Python is added.
- New test files: **none** (prose deliverable; artisanal verification per project invariant).

## Implementation Plan

1. **Create the skill directory + front-matter.**
   - Files: `skills/sr-query/SKILL.md` (new).
   - Changes: YAML front-matter — `name: sr-query`; `description:` (a crisp, model-invocation-facing one-liner: "Run read-only SQL against your local warehouse of agentic-coding history" — phrased so the agent reaches for it on exact/structured-lookup tasks); `license: "Multiple — see LICENSES/ and REUSE.toml"`; `enable-model-invocation: true`.

2. **Write the "When to use this" / routing section.**
   - Files: `skills/sr-query/SKILL.md`.
   - Changes: Describe the surface (raw read-only SQL over the DuckDB warehouse) and *when it is the right tool* — exact ids, structured `WHERE`/`COUNT`/`GROUP BY`/joins, "I know the shape of what I want." Contrast briefly with meaning-based lookup (point to `sr-semantic`, to be authored next) so an agent doesn't misuse SQL `ILIKE` as a semantic search. Keep it short — judgement detail belongs to the future `sr-search`.

3. **Write the invocation contract section.**
   - Files: `skills/sr-query/SKILL.md`.
   - Changes: The plugin-root resolution preamble (`CURSOR_PLUGIN_ROOT` with the `find -L ~/.cursor/plugins …/skills/sr-search/pyproject.toml` fallback) and the torch-safe run (`uv run --project "$APP_DIR" --no-sync python -m stockroom.query …`), copied faithfully from `sr-search`'s SKILL.md + `systemPatterns.md`. Note: resolve `APP_DIR` **once** per session and reuse it; the engine home is `skills/sr-search` even though this is the `sr-query` skill (shared engine).

4. **Write the flags + output-discipline section (`--format` / `--detail`).**
   - Files: `skills/sr-query/SKILL.md`.
   - Changes: Encode the `print-for-who.md` skill contract: default invocation is already safe (`tsv` + `snippet`); reach for `--detail full` when a needed field shows `…(+N)`; `--detail compact` to scan many rows cheaply; offer `--format table` (human) / `--format json` (structured) **only when the user asks** for a copy-paste command or those shapes. State the elision marker meaning (`…(+N)` = N more chars exist, full content is whole at rest).

5. **Write the guardrails section.**
   - Files: `skills/sr-query/SKILL.md`.
   - Changes: Context-blowout avoidance (explicit narrow column lists + `LIMIT`, not `SELECT *` at `--detail full` over many rows); read-only contract (no DML — DuckDB rejects it; surfaced as `query failed:`; do not retry writes); failure handling without thrashing (map the three exact stderr forms — `error: empty query …` exit 2, `error: no warehouse found … run python -m stockroom.ingest first` exit 1, `query failed: …` exit 1 — each to the right next action: fix SQL, tell the user to ingest, or correct the statement).

6. **Write the schema-orientation section + worked examples.**
   - Files: `skills/sr-query/SKILL.md`.
   - Changes: **Lead with introspection, not a hard-coded map** (preflight radical-innovation amendment — keeps the skill self-maintaining across future migrations `0004+` and directly discharges the "example SQL drifts from schema" challenge): teach the agent to discover the live schema first via a copy-paste query, e.g. `python -m stockroom.query "SELECT table_name, column_name, data_type FROM information_schema.columns ORDER BY table_name, ordinal_position"`. **Then** give a compact quick-reference map of the load-bearing tables/columns explicitly labelled *"as of migrations 0001–0003 — confirm with the introspection query above"* (`sessions`: `harness`, `session_id`, `project_id`, `cwd`, `models`; `messages`: `message_id = {session_id}#{ordinal}`, `harness`, `text`, `model`, the four token `BIGINT`s; `tool_calls`: inputs-only, `tool_input` JSON via `->`/`->>`; `embeddings`; `_sync_state`) — grounded in `systemPatterns.md` "Harness-labeled schema" + `techContext.md` "Warehouse Schema". 2–3 copy-paste example invocations: the default tsv call, a `--detail full` re-fetch, and a `--format table`/`json` variant. **Verify every example's SQL against the live schema** before finalizing (run them through the engine if a warehouse exists, else against the `0001`/`0002`/`0003` migration DDL) so no example ships a non-existent column.

7. **Documentation cross-references + skeleton-skill note.**
   - Files: `skills/sr-search/SKILL.md` (small edit), `skills/sr-query/SKILL.md`.
   - Changes: Update `sr-search`'s SKILL.md line that says the `/sr-query` wrapper is "Phase 5 distribution work" — it now exists. Keep edits minimal and factual. (No `plugin.json` edit: both manifests auto-discover `./skills/`. No `REUSE.toml` edit: glob-covered.)

## Technology Validation

No new technology — validation not required. No new runtime dependency, no schema/migration, no build-tool change. The wrapped surface (`stockroom.query` + `render` + `truncate`) already ships and is fully tested.

## Dependencies

- Existing engine surface `python -m stockroom.query` with `--format {tsv,json,table}` (default `tsv`) and `--detail {compact,snippet,full}` (default `snippet`) — landed in m3/m3.5 (`skills/sr-search/src/stockroom/{query,render,truncate}.py`).
- The plugin-root resolution + torch-safe invocation contract (`systemPatterns.md`; `sr-search/SKILL.md`).
- Skill front-matter conventions (`sr-search/SKILL.md`); `REUSE.toml` `skills/**` glob; plugin auto-discovery via `"skills": "./skills/"`.
- The settled output/skill contract in `planning/brainstorm/print-for-who.md` and the architecture in `creative/creative-search-surface-architecture.md`.

## Challenges & Mitigations

- **Prose deliverable vs. the TDD rule.** *Mitigation:* the project invariant (`milestones.md` / `creative-search-surface-architecture.md`) explicitly verifies prompt-skills artisanally and binds TDD to Python only; this sub-run writes no Python, so the gate is `make ci` green + `make reuse`. Documented above so preflight doesn't read "no tests" as a defect.
- **Example SQL drifting from the real schema.** *Mitigation:* step 6 verifies every example column against the live warehouse (or the migration DDL `0001`/`0002`/`0003`) before finalizing — a shipped example that references a non-existent column would teach the agent wrong SQL.
- **Duplicating judgement that belongs to `sr-search`.** *Mitigation:* keep routing guidance thin — "is this an exact/structured lookup?" — and leave the keyword-vs-semantic-vs-both *decision* to the future `sr-search` skill; `sr-query` only owns its own surface's safe use.
- **Helper-script temptation / scope creep toward L3.** *Mitigation:* explicitly prose-only this sub-run (decision above); if a shared resolver proves warranted it is a deliberate later choice by `sr-semantic`/`sr-search`, not smuggled in here.

## Preflight Findings (2026-06-30)

- **PASS.** TDD-encoding check passes by exemption: prose deliverable, no Python, artisanal verification per the project invariant — not the "implementation-without-tests" anti-pattern. Convention/conflict/completeness all clean.
- **Amendment applied** (radical-innovation, in scope): step 6 now leads with a live schema-introspection query and labels the static column map "as of migrations 0001–0003", so the skill stays correct across future migrations without edits and the example-drift challenge is structurally mitigated.
- **Advisory → routed to REFLECT (not a build task):** `techContext.md` "Query (`sr-query`)" says "The polished `/sr-query` skill wrapper and per-harness invocation forms are Phase 5 distribution work." Once this skill ships, the *wrapper* half of that sentence is stale (per-harness invocation forms remain Phase 5). Per the niko lifecycle (m3.5 precedent), persistent-doc reconciliation happens at REFLECT, not BUILD — flagged here so REFLECT catches it. The `semantic.py`/techContext "Semantic search" section carries the identical Phase-5 line and should be reconciled when `sr-semantic` lands (next milestone), not now.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [ ] Build
- [ ] QA
