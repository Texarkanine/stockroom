---
task_id: p1-data-backbone
complexity_level: 4
date: 2026-06-28
status: completed
---

# TASK ARCHIVE: Phase 1 — Data Backbone (Schema, Migrations, Ingest, Query)

## SUMMARY

Phase 1 built the faithful data backbone of stockroom: a real ingest of the operator's own Cursor and Claude Code history now lands faithfully in a queryable single-file DuckDB warehouse under `~/.stockroom/`, sitting on a forward-only numbered migration system, with `python -m stockroom.query` as the first user-facing read surface. The schema → migration framework → ingest → query loop is demonstrably end-to-end: a freshly ingested throwaway warehouse answers `SELECT DISTINCT harness` with both `cursor` and `claude`, exercised as a subprocess test.

Executed as a Level 4 project across five sequential, dependency-ordered milestones, each its own L1–L3 sub-run. Every milestone closed green (`make ci`) and passed QA before its reflection. The project also dogfooded its own infrastructure: milestone 4 became the migration framework's first real data-preserving schema upgrade (`0002`).

## REQUIREMENTS

From the Phase 1 project brief ("Done When"):

- A real ingest of the operator's own Cursor and Claude Code history lands faithfully — kept fields stored whole and verified against the source, subagents linked to parents.
- `sr-query` returns correct results over it.
- The migration suite proves a schema-changing upgrade is safe and data-preserving under concurrent reader/writer load.

Cross-milestone invariants held throughout:

- **No truncation at rest** — kept content stored whole; truncation is a read-time concern only.
- **Harness-labeled, one shared schema** — every content row carries a `harness` column; never per-harness tables.
- **Tool inputs only** — tool calls store inputs, never outputs; no raw layer persisted.
- **Schema changes only via new numbered, forward-only migrations** — no migration ever mutated.
- **Clean-room boundary** — Claude Code support reverse-engineered from its own on-disk format; no `claude-warehouse` code or unique ideas.
- **Locked-uv trust** — no new runtime dependency entered without `make lock`; torch held out of the lock.
- **Harness-neutral warehouse home** — the warehouse lives under `~/.stockroom/`, not beneath any harness's directory.
- **Test-first** and **green gate** (`make ci`) at every milestone boundary.

## IMPLEMENTATION

The backbone lives in the `sr-search` engine package (`skills/sr-search/src/stockroom/`):

- **Schema** (`migrations/0001_initial_schema.sql`) — five harness-labeled tables (sessions, messages, tool calls inputs-only, embeddings, sync-state watermark) with the stable message-identity contract (`message_id = {session_id}#{ordinal}`, composite PKs) and conversation-reconstruction keys (conversation id, parent/child, ordering, subagent↔parent, model-per-chain). Model split by grain (`messages.model` vs `sessions.models VARCHAR[]`); typed BIGINT tokens; native LIST; JSON only for `tool_input`. No FKs, no harness CHECK, no HNSW index — each a deliberate, test-guarded omission. The Project Brief's sixth table (`plan_documents`) was dropped in creative with operator approval. Locked by a golden `0001_snapshot.json`.
- **Migration framework** (`migrations/__init__.py` discovery, `migrate.py` runner, `warehouse.py` chokepoint) — numbered one-per-file forward-only SQL, a runner-owned `schema_version` table, a lazy version gate inside the single `warehouse.open()` chokepoint, transactional application under an `fcntl.flock` single-writer token (over DuckDB's native lock) with bounded reader backoff. Writer flock release bound to connection finalization via `weakref.finalize`.
- **Trace ingest** (`ingest/` package: `model.py`, `cursor.py`, `claude.py`, `sources.py`, `enrich.py`, `writer.py`, `__init__.py` orchestrator, `__main__.py` CLI) — incremental `(mtime, path)` watermark per `(harness, source_root)` with `--full` reset; both harnesses parsed clean-room from native formats; subagents linked to parents (Claude via `meta.json` `toolUseId`→parent `Task` provenance; Cursor structurally via `subagents/`); kept content untruncated; tool inputs only; optional `ai-code-tracking.db` model enrichment as a graceful no-op. Locked by a byte-for-byte golden `expected_rows.json`.
- **Workspace identity** (`migrations/0002_workspace_identity.sql`, `ingest/paths.py`) — replaced the lossy fabricating `project_path` with `project_id` (verbatim slug, the grouping identity) + an honestly-NULL `cwd` (real project root) recovered by a verify-don't-invert resolver (re-encode candidate paths and match the slug); shipped as the framework's first real data-preserving migration.
- **Query surface** (`query.py`) — a single runnable module (`python -m stockroom.query`) opening the warehouse `read_only=True` through the chokepoint, running arbitrary SQL, printing a column-aligned table with an always-on `(N rows)` trailer. Read-only enforcement is the open mode, not app logic.

## MILESTONE LIST

Original plan (project brief) listed **four** milestones: schema, migration framework, ingest, `sr-query`. Execution ran **five**:

1. [x] **Schema field enumeration + locked DDL** *(L3)*
2. [x] **Migration framework** *(L3)*
3. [x] **Trace ingest (ETL)** *(L3)*
4. [x] **Workspace identity vs. real path (`project_id` + `cwd` recovery)** *(L2)* — **added during execution**
5. [x] **`sr-query`** *(L2)*

**Re-scope note:** Milestone 4 was inserted after ingest landed. Ingest revealed that the encoded project-dir slug was being lossily decoded into a *fabricated* path (`decode_project_dir`). Milestone 4 corrected the path model — splitting `project_path` into verbatim `project_id` + honestly-NULL recovered `cwd` — and, by doing so, became the migration framework's first real data-preserving upgrade (`0002`), satisfying the Phase-1 "Done When" requirement that the migration suite prove a safe schema-changing upgrade. No milestones were removed or reordered.

## SUB-RUN SUMMARIES

### Milestone 1 — Schema field enumeration + locked DDL (L3)

Locked the five-table harness-labeled schema as `0001`, authored test-first (46-test contract suite + golden snapshot) with durable native-format transcript fixtures reused downstream. **Key decisions:** uniform `message_id`, model split by grain, typed tokens / native LIST / JSON-only-for-tool_input, deliberate no-FK/no-CHECK/no-index omissions each proven by a test. **Friction:** trivial only — a JSON `len()`-vs-`json_array_length` test bug and DuckDB internal catalog tables sweeping into the first snapshot (fixed with `internal = false`). A planning-time POC against the real DuckDB version meant zero engine surprises at build.

### Milestone 2 — Migration framework (L3)

Built the forward-only numbered-SQL subsystem: discovery, a transactional runner with a runner-owned `schema_version` table, and the single `warehouse.open()` chokepoint with an `fcntl.flock` writer token over DuckDB's native lock plus bounded reader backoff. **Key decisions:** Option A (flock writer/migrator token + `schema_version` bootstrap table); the concurrency suite required **zero** production changes — the strongest signal the design translated cleanly. **Friction:** the creative doc named the lock policy but not the *mechanism*; build discovered `DuckDBPyConnection` rejects attribute assignment but supports weakrefs, so `weakref.finalize` binds flock release to connection finalization (GC-timing-dependent, noted). Two pre-plan POCs (DuckDB cross-process lock model; flock auto-release on WSL ext4) bought a first-try-green concurrency suite.

### Milestone 3 — Trace ingest / ETL (L3)

Built the incremental watermarked `stockroom.ingest` filling the schema from real Cursor + Claude Code history through the chokepoint. **Key decisions:** clean-room parsers per harness; subagent linkage at session grain; untruncated kept content, inputs-only; idempotent delete-then-insert re-ingest; empty-session resolves to "session row with 0 messages." **Friction:** none substantive — QA found only a non-blocking DRY observation (duplicated `_iter_records`, correctly left alone under the clean-room boundary). **The single biggest accuracy driver was a pre-plan structural probe of the operator's real logs** — it proved branching `parentUuid` chains are real, making the uuid-tree-to-nearest-kept-ancestor walk mandatory; a fixtures-only plan would have shipped positional linking and silently corrupted reconstruction. Locked by a golden `expected_rows.json`.

### Milestone 4 — Workspace identity / `cwd` recovery (L2)

Replaced the lossy fabricating `project_path` with `project_id` (verbatim slug) + honestly-NULL `cwd`, shipped as the framework's first real data-preserving migration `0002`, with a corpus-wide no-fabrication round-trip invariant. **Key decisions:** verify-don't-invert resolver (`encode_for(harness, candidate) == slug`) — zero false-positive rate by construction, clean-NULL failure mode; `decode_project_dir` deleted. **Friction:** the plan's commit granularity was wrong — introducing `0002` advances the migration head to v2, breaking every test that hard-coded "version 1 / only 0001 exists" *and* the CLI integration tests (warehouse migrates to v2 while the not-yet-renamed writer still inserts `project_path` → BinderError). The coupled steps had to land as one atomic green commit. **Million-Dollar Question:** had honest workspace identity been foundational, `0001` would have declared `project_id`+`cwd` from the start, eliminating `0002` and the dual-snapshot churn — but the migration was valuable on its own terms as the framework's first real upgrade.

### Milestone 5 — `sr-query` (L2)

Shipped `python -m stockroom.query`: a single runnable module opening the warehouse read-only through the chokepoint, running SQL, printing an aligned table with a `(N rows)` trailer. Green first try on every step; QA clean, no rework. **Key decisions:** read-only is the open mode (DuckDB rejects writes — no app-level allow/deny-list); single-file module (no `__main__.py`) for a cohesive one-surface tool; one deterministic text format (YAGNI on `--format`); `(N rows)` trailer makes proof-of-queryability output self-describing. **Friction:** none — a benign RED false-positive (empty-SQL test passing because stubbed `main` raised `NotImplementedError`). This milestone closed the Phase-1 loop: the end-to-end DISTINCT-harness subprocess test *is* the "Done When" proof at the query layer.

## SYSTEM STATE

What exists now that didn't before:

- A populated, queryable single-file DuckDB warehouse at `~/.stockroom/` (harness-neutral home).
- The `stockroom` engine package with four cooperating subsystems behind one `warehouse.open()` chokepoint: schema (migrations `0001`+`0002`), the migration framework (discovery + runner + flock/backoff), the `ingest` ETL package (two clean-room parsers, watermark state, path resolver, subagent linkage, enrichment), and the `query` read surface.
- Two operator-facing entrypoints: `python -m stockroom.ingest [--full] [--harness …]` and `python -m stockroom.query "<SQL>"`.
- Three layers of golden-snapshot regression guards (schema snapshot, `open()`/migrated-schema guard, ingest-output snapshot) plus a corpus-wide no-fabrication round-trip invariant.

End-to-end integration: `ingest` writes through the lazy-migrating, single-writer-locked chokepoint; `query` reads through the same chokepoint read-only. A behind warehouse is migrated forward on first open by whoever opens it (reader-turned-migrator). The schema is harness-labeled and shared, so a single query is cross-harness by omitting the column or per-harness by filtering it.

## TESTING

Test-first throughout (workspace TDD rule). Each milestone gated on green `make ci` (sync, lock-check, lint, format-check, full test suite, REUSE) and passed `/niko-qa` semantic review before reflection. Final suite: **184 tests passing**, ruff clean, `uv.lock --locked`, REUSE 156/156.

Verification highlights:

- **Faithful capture** locked by a byte-for-byte golden ingest snapshot (`expected_rows.json`) covering every ordinal, parent_id, drop, token, and subagent edge.
- **Safe schema upgrade under concurrency** proven by milestone 2's outcome-based concurrency suite (writer flock + reader backoff) and exercised for real by milestone 4's `0002` data-preserving migration.
- **End-to-end queryability** proven by milestone 5's subprocess test: ingest a throwaway warehouse, then `SELECT DISTINCT harness` names both `cursor` and `claude`.
- **No fabrication** proven by milestone 4's corpus-wide round-trip invariant (a fabricated path cannot be stored).

## LESSONS LEARNED

- **Spike the load-bearing primitive before designing on it.** Every milestone that did a planning-time POC against the real engine/data (m1 DuckDB feature-set, m2 flock/lock model, m3 structural log probe) hit a frictionless build. The probes converted the dominant unknown from assumption to evidence — branching `parentUuid` chains (m3) is the standout: no fixture would have surfaced it.
- **The "golden output generated by the test's own query helper" pattern is the project's most reliable correctness lever.** Used at three layers (schema snapshot, `open()` guard, ingest snapshot); generator and assertion share a code path so they can't silently diverge, and the diff *is* the review surface for any intentional change.
- **Read-only is enforcement-for-free.** A pure read surface should open `read_only=True` and lean on the engine to reject writes — no validation layer to build, test, or get wrong.
- **Scope risk lives in shared mutable globals, not line count.** The two L2 milestones diverged sharply: m4 (touches the migration head, a shared global) forced an atomic multi-file commit; m5 (purely additive) was the cheap case. Recognizing this up front predicted both builds.
- **A new migration is a test-suite-wide event, not a local file add.** Adding `0002` rippled into every test asserting "latest version == N" or opening the real warehouse, plus the CLI integration tests. Budget head-version-assertion updates as part of any migration change.
- **Verify-don't-invert is the durable shape for any lossy harness encoding.** A many-to-one `encode` can't be inverted but can be recomputed forward and checked — false-positive rate zero by construction, failure mode a clean NULL.

## PROCESS IMPROVEMENTS

- **Add "migration-count / head-version assumptions" to the preflight dependency sweep.** Preflight correctly enumerated every `project_path` symbol consumer but missed the tests coupled to the migration *head* — the one surprise of milestone 4. A cheap checklist addition whenever a task adds a migration.
- **"Every commit stays green" can legitimately override "one commit per plan step."** When steps are coupled through a shared global (the migration head), collapsing them into one atomic green commit is the correct bisect-safe move — TDD discipline lives in the RED→GREEN iteration, not the commit count.
- **A creative phase is correctly skippable when the only residual unknown is empirical, not architectural** — but the skip must be *earned* by an actual probe (m3), not assumed.
- **The L4 milestone decomposition held up well.** The strictly-sequential dependency order (schema → framework → ingest → query) meant each sub-run read/built on verified artifacts; the one inserted milestone (4) arose from real evidence (ingest output) rather than plan drift.

## TECHNICAL IMPROVEMENTS

- DuckDB has transactional DDL — `CREATE TABLE` inside an explicit transaction rolls back on failure, making "atomic or nothing" migrations trivial to assert.
- DuckDB introspection (`duckdb_columns()`) returns system catalog tables in the `main` schema — any snapshot/reflection logic must filter `internal = false`.
- `DuckDBPyConnection` is a C type (no attribute assignment) but supports weakrefs — `weakref.finalize` is the clean way to bind an external resource (flock fd) to connection lifetime. Note the release is GC-timing-dependent (fires on finalization, not `con.close()`); a future resource with stricter timing needs would want an explicit close path.
- `flock` conflicts per open-file-description, so the basic lock primitive is unit-testable within one process via two `os.open()` fds; the genuine cross-process *conflict* path needs a real subprocess.

## NEXT STEPS

- **Phase 2** (per `planning/roadmap.md`): read surfaces over the warehouse, where the "read surfaces open read-only; DuckDB enforces immutability" pattern (recorded in `systemPatterns.md`) becomes load-bearing; truncation enters as a read-time concern.
- **Phase 5** (deferred from milestone 5): the `skills/sr-query/` skill wrapper + per-harness `/sr-query` invocation, and richer query output formats (`--format {csv,json}`) — deliberately scoped out to keep milestone 5 at L2.
- Memory bank is clean and ready for the next task.
