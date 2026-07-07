# Task: `sr-semantic` skill (p2-embeddings-search m5)

* Task ID: p2-embeddings-search-m5
* Complexity: Level 2
* Type: simple enhancement (prose skill authoring)

Author `skills/sr-semantic/SKILL.md` — the safe, ergonomic LLM wrapper over the already-built pure vector-search surface (`python -m stockroom.semantic`). The skill is the single home for the operational knowledge that keeps an agent safe and effective on this surface: when to reach for semantic search (vs. `sr-query` / `sr-search`), how to phrase queries, the verified invocation contract, `-k` / `--format` / `--detail` output discipline, and guardrails against context blowout, wasted tool calls, and this surface's torch dependence. Structurally the sibling of the m4 `sr-query` skill; prose-only (no helper `scripts/`, no Python — m4 precedent).

## Test Plan (TDD)

**TDD exemption (project invariant):** the deliverable is prose (SKILL.md); no Python is written, so the TDD rule binds nothing here. Prompt-skill behavior is verified **artisanally** by the operator. The build-time verification obligations below substitute for a test suite:

### Behaviors to Verify (artisanal, at build time)

- Invocation contract → every shipped command (`APP_DIR` resolution + `PYTHONPATH="$APP_DIR/src" uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom.semantic …`) executes successfully against the live warehouse before being written into the skill.
- Default call (`"<query>"`, no flags) → tsv header `rank score harness role preview` + ≤10 rows, previews bounded at `snippet` (~120 chars) with `…(+N)` elision markers on over-budget previews.
- `-k N` → at most N ranked rows; `-k 0`/negative → stderr `error: --limit must be a positive integer`, exit 2.
- Empty query (`""`) → stderr `error: empty query …`, exit 2.
- `--format json` → single `{"results": [...]}` object additionally carrying `session_id`/`message_id` and numeric `score`; `--format table` → aligned table with `(N results)` trailer.
- `--detail full` on a scoped re-run → untruncated text (display bound only; store unaffected).
- The full-text handoff to `sr-query` (fetch one hit's whole `text` by `message_id` at `--detail full`) → verified live end-to-end.
- Missing warehouse path documented from the code's actual stderr form (`error: no warehouse found at … — run `python -m stockroom.ingest` first`, exit 1) — not invented.

### Test Infrastructure

- Framework: none required (prose deliverable). Automated gate: `make ci` green (existing 266-test suite must not regress) + REUSE compliance (new SKILL.md covered by the existing `skills/**` glob).
- New test files: none.

## Implementation Plan

1. ✅ **Skeleton + front-matter** — create `skills/sr-semantic/SKILL.md` with front-matter mirroring `sr-query`: `name: sr-semantic`; a routing-bearing `description` (meaning-based recall over agentic-coding history — concepts/paraphrase, not exact ids/filters, which are `sr-query`); `license: "Multiple — see LICENSES/ and REUSE.toml"`; `enable-model-invocation: true` (live skill).
   - Files: `skills/sr-semantic/SKILL.md` (new)
2. ✅ **When-to-use / routing section** — semantic search is for *meaning-based* recall ("find conversations about flaky tests", paraphrased/conceptual queries); route exact/structured lookups to `sr-query`; uncertain routing belongs to `sr-search`. Include query-phrasing guidance: natural-language phrases describing the content sought; the bge asymmetric query prefix is applied automatically — never hand-add it.
   - Files: `skills/sr-semantic/SKILL.md`
3. ✅ **Invocation contract** — the shared `APP_DIR` resolution block + torch-safe run contract, verbatim from the (m4-corrected) canonical form, with the three load-bearing details (`PYTHONPATH`, `--no-sync`, `--no-config`). Add the surface-specific fourth: **this surface needs torch at query time** (the encoder embeds the query), so `--no-sync` is doubly load-bearing and a torch-missing failure is an environment problem — do not retry; tell the user to provision torch (repo dev: `make torch`).
   - Files: `skills/sr-semantic/SKILL.md`
4. ✅ **Output discipline** — `-k/--limit` (default 10; when to raise/lower), `--format` (tsv default, json for structured/user-asked, table for human-readable) and `--detail` (compact/snippet/full) tables in the m4 style; document the semantic output columns per format (`rank score harness role preview`; json adds `session_id`/`message_id` + numeric `score`; `score` is cosine similarity, higher = closer).
   - Files: `skills/sr-semantic/SKILL.md`
5. ✅ **Guardrails** — (a) context blowout: never `--detail full` with a large `-k`; scan at default `snippet`, then fetch the one hit you want — the canonical full-text fetch is a **`sr-query` handoff by `message_id`** (composability; json format carries the ids); (b) read-only by construction; (c) error table from live stderr/exit codes (empty query 2, bad limit 2, missing warehouse 1) with the matching non-thrashing next action; (d) relevance judgement: scores are relative, not absolute — read the previews, don't threshold blindly; (e) *(preflight amendment)* silent-staleness: semantic search only sees what has been **embedded** — embeddings can lag ingestion, so weak/missing results for recent work are a coverage symptom, not proof of absence; check via the `sr-query` handoff (`SELECT count(*) FROM embeddings` / compare against recent `messages`) and suggest `python -m stockroom.embed` (incremental) rather than re-phrasing the query in a loop.
   - Files: `skills/sr-semantic/SKILL.md`
6. ✅ **Worked examples + relaying-to-a-human** — a verified example block (default call; `-k 5`; json for ids; the sr-query full-text handoff pair) — every example executed live against the real warehouse first; close with the m4 "you are the operator, not the display" relaying section.
   - Files: `skills/sr-semantic/SKILL.md`
7. ✅ **Integration checks + gate** — confirm `sr-search/SKILL.md` needs no edit (its entrypoint list already names `stockroom.semantic`; its invocation block was m4-corrected); no `plugin.json` edit (skills auto-discovered), no `REUSE.toml` edit (glob-covered); re-run `make localdev` so the new skill dir is mirrored into `.cursor/skills/stockroom-local/`; run full `make ci`; restore out-of-band torch via `make torch` after the CI sync strips it (m4 precedent).
   - Files: none expected beyond the new SKILL.md (verification-only step)

## Technology Validation

No new technology — validation not required. (No new dependency, no schema/migration, no build-tool change. Torch is the existing Phase-0 out-of-band provision, exercised — not introduced — by the live-example verification.)

## Dependencies

- Live warehouse at `~/.stockroom/` with **populated `embeddings` rows** (m1 pipeline output) — required for meaningful live example verification.
- Out-of-band torch present in the engine venv at verification time (`make torch` restores it if a sync stripped it).
- m4 `sr-query` skill (the routing counterpart and full-text handoff target) — shipped.

## Challenges & Mitigations

- **Torch stripped by the CI sync** (m4 hit this): run `make ci` *before* final live-example re-verification, or re-run `make torch` after; verify with a live semantic call last.
- **Embeddings coverage may be stale/empty** → before writing examples, check `SELECT count(*) FROM embeddings` via `stockroom.query`; if empty/stale, run `python -m stockroom.embed` (incremental) first.
- **Example drift as the schema/model evolves** → keep examples minimal and behavior-anchored (the m4 introspection-first pattern doesn't apply here — there is no schema to introspect — so anchor on the stable CLI contract and label the output-column list with its source, `stockroom.render` as of m3.5).
- **First encoder use may download the model** → the m1/m2 work already cached `bge-small-en-v1.5` locally; if a fresh environment stalls on download, that is environment provisioning, not a skill defect.
- **`techContext.md` "Semantic search" Phase-5 wording goes partly stale** once the wrapper ships → REFLECT-phase reconciliation (m4 precedent), not a build task.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD — exemption documented)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Preflight
- [x] Build
- [x] QA — PASS (one trivial fix: labeled the `--format` shapes/columns table with its source, the shared `stockroom.render` layer, per the plan's example-drift mitigation; `make ci` re-run green, torch restored)
