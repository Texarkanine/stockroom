# Brainstorm — Skill Litter Audit

Audit record (2026-07-07): an inventory of "by the way" explanatory content in the shipped `sr-query` / `sr-semantic` SKILL.md files, a recommended understand-vs-do split, and where each finding should go. Recorded for later action — nothing here has been applied.

Feeds: the `sr-search` skill milestone (m6, `memory-bank/active/milestones.md`), then Phase 4 (`sr-initialize`) via `stockroom-on-path-cli.md`, which supersedes the largest litter category outright.

## Problem

Each wrapper skill currently serves two different readers: the agent **executing a task** (needs the incantation, flags, error → next-action, schema) and the agent **needing to understand the system** (off-table errors, "how does stockroom work?", debugging). Every execution pays the token cost of the understanding material even though most invocations never need it. Worse, the rationale is repeated across sibling skills — the exact drift setup that let the invocation contract go stale in N places before the m4 sub-run fixed it.

The test for litter is not "is this explanatory?" but **"does the agent need this to act correctly or recover from failure right now?"** Rationale fails that test; recognition-and-recovery passes it.

## Recommended split

- **Skills keep task knowledge only**: routing ("when to use this vs. the sibling"), the incantation, flags, guardrails-as-actions, error tables with next actions, the schema quick-reference (`sr-query`), score semantics (`sr-semantic`).
- **A shared reference doc holds the system model**: torch contract, run-in-place packaging (`[tool.uv] package = false`), ETL / read-only-by-construction, no-truncation-at-rest doctrine, embedding pipeline and staleness model, identity/provenance philosophy.
- **Each skill carries one pointer** to the shared doc ("to understand why this contract looks the way it does, read …"), fetched on demand — progressive disclosure, not guaranteed pre-loading. The plugin is a closed stack and skills already resolve `$APP_DIR`, so the cross-reference is safe and the path is in hand.
- **The doc holds *why*, skills hold *do*.** If the shared doc starts restating operational rules, the drift problem returns with a second head.

The deepest fix for the invocation-litter cluster is not documentation at all: most of it exists because the incantation is fragile (three flags that each break the call if omitted). The on-path `stockroom` CLI (`stockroom-on-path-cli.md`) removes the fragility, and with it the need for the annotations. Trim after (or with) that change, not before.

## Inventory

### Category A — pure rationale, move to the shared doc

- Both, invocation section: "(it is the shared stockroom engine; `<skill>` has no Python of its own)"; "with a filesystem fallback for symlinked dev installs" (the code block already shows the fallback); "the torch-safe run contract" jargon.
- Both, `PYTHONPATH` bullet: "the engine is a run-in-place project (`[tool.uv] package = false`), so `stockroom` is not installed on `sys.path`" — keep only the error signature.
- Both, `--no-config` bullet: "keep ambient `~/.config/uv/uv.toml` out of resolution (hermetic, matches the repo's `Makefile`)" — the instruction is just "always pass it."
- `sr-query`, `--no-sync` bullet: "(the project's torch contract). `sr-query` itself does not need torch, but its sibling surfaces share the environment" — pure why, in a skill that does not use torch.
- `sr-query` intro: "it is rebuildable ETL output."
- `sr-semantic` intro: "runs cosine KNN over the HNSW index"; "same local model that embedded the stored messages" is borderline (the phrasing section already carries the actionable half).
- `sr-query` JSON guardrail: "when the planner evaluates it on a differently-shaped row" — the fix stands without the planner theory.
- `sr-query` identity notes: the "demoted to provenance columns" framing — the actionable half is "join on `message_id` / `(harness, session_id)`, never on `source_*`."

### Category B — doubled content, one copy should win

- `sr-semantic`: torch-missing advice appears twice — the "two runtime notes" paragraph *and* the error-table row. The table row suffices.
- Both: the no-truncation-at-rest doctrine sentence in each `--detail` section. An agent needs one clause ("truncation is display-only; full text is retrievable"), not the philosophy.
- Both: the three annotated flag bullets are near-identical across the two files — the largest single duplication, eliminated outright by the on-path CLI.

### Category C — narration and reassurance padding, cut without replacement

- Both intros: "This skill is the safe, ergonomic way for an agent to drive that surface without flooding its own context window or burning failed tool calls" — the skill describing itself; the guardrails *are* that content.
- Both: "Two/Three independent axes control output" — structural narration; the subheadings already show it.
- `sr-semantic`: the em-dash restatement in the output-discipline lead ("— a bare call gives ≤10 ranked rows with bounded previews —") pads the single operational claim, "the defaults are safe; touch flags only when needed."
- `sr-semantic` `--format` lead-in: "Shapes and columns as rendered by the shared `stockroom.render` layer (verify against a live call…)" — maintenance metadata for authors, not operators; belongs in the shared doc.

### Category D — looks like litter, keep as operational recognition/recovery

- Error signatures inline (`ModuleNotFoundError: No module named 'stockroom'`) — failure recognition.
- "A sync strips torch and this surface needs torch at query time" — the consequence that makes `--no-sync` non-negotiable for `sr-semantic` (moot once the CLI owns the flag).
- "Embeddings can lag ingestion" — required to act on the staleness guardrail.
- Score semantics ("similarity, higher = closer, relative — don't threshold"); the stderr-noise note (could be half its length); "thinking is not captured"; the query-prefix doubling warning (could shrink to "applied automatically; don't add it").

## Magnitude and sequencing

Categories A–C are roughly a quarter to a third of each skill's prose, concentrated in the intro and invocation sections. The invocation cluster — the largest — is mooted by the on-path CLI, so the economic order is:

1. Finish m6 (`sr-search`) against the current contract; accept that its invocation section inherits the same litter temporarily.
2. Land the on-path `stockroom` CLI in Phase 4 (`sr-initialize`) per `stockroom-on-path-cli.md`.
3. One trimming pass across all three wrapper skills: swap incantations for `stockroom <subcommand>`, apply this inventory, add the shared-doc pointer.
