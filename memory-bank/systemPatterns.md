# System Patterns

## How This System Works

Stockroom is forward-looking — almost no product code exists yet, so this document is **lightly seeded from the planning docs and is expected to accrete** as the build reveals which patterns actually hold. The mental model needed before touching anything:

- The central trust decision is that stockroom ships as a **locked uv *project*** (not loose `uv run --script` files): everything pinned and hash-verified through a committed `uv.lock` — **except torch**, the single deliberate exception.
- The warehouse is a **single-file DuckDB** database in a **harness-neutral** home (`~/.stockroom/`), not buried under any one harness's directory.
- **Faithful capture is the reason the product exists**: kept fields are stored *whole* (no truncation at rest); truncation exists *only at read time*. Conflating these two is the exact mistake the reference tools made.
- Ingest is **ETL, not mirroring**: kept fields reshaped into stockroom's schema, **tool inputs only** (no outputs), no verbatim raw layer.
- The schema is **harness-labeled** (one shared set of tables, a `harness` column per row) and is designed **empirically** from real logs, not transliterated from any reference.
- **Migrations are first-class from Phase 1** (forward-only, `schema_version` record, lazy gate, exclusive write lock, concurrency-safe reader degradation). "Never break your warehouse" is a tested promise.
- **Hook discipline**: the session-start hook *only* launches the dashboard — never ingests, never migrates, never errors.

Memory-bank strategy: the rich `planning/` docs are authoritative during the build; durable knowledge accretes here, and the docs are distilled away and deleted at the final roadmap step (see `productContext.md` / `techContext.md` cut gates).

## Locked uv project, torch held out of the lock

The load-bearing packaging pattern. Lock everything hermetically with `uv lock --no-config`; exclude torch via an impossible environment-marker override (`override-dependencies = ["torch; python_full_version < '3'"]`) so it never enters the lock, then provision it per-machine out of band (`uv pip install torch --no-config --index <wheel-url>`). **After torch is installed, never run an exact sync** (`uv run --no-sync`, or `--inexact` when a sync is genuinely needed) — a bare sync deletes it. Proven end-to-end in `planning/spikes/o9-torch/`; full rationale in tech-brief → "The Torch Exception".

## No truncation at rest; truncation is a read-time feature

Kept content (prompts, responses, tool inputs) is stored in full. Output truncation is applied only at read time (chiefly in `sr-search`), sized to answer without flooding the caller's context window. Storage-time caps are the failure mode stockroom exists to correct — do not reintroduce them.

## Harness-labeled schema, designed empirically

One shared set of tables (sessions, messages, tool_calls inputs-only, plan_documents, embeddings, `_sync_state`), every row carrying a `harness` column — never per-harness tables. Conversation reconstruction is first-class (conversation id, parent/child, ordering, subagent↔parent edge, model-per-chain) atop a stable message-identity contract. Concrete DDL is derived test-first from real Cursor + Claude Code logs (the first Phase 1 task).

## Dual-manifest plugin, no build step, app inside one skill

Ships from the `slobac` template as a `.cursor-plugin/plugin.json` + `.claude-plugin/plugin.json` over a shared `skills/` tree, **committed layout = install layout** (no build), versioned by release-please which syncs the version into both manifests. **Unusually, one skill directory also contains the full Python app** (`pyproject.toml`, `uv.lock`, migration SQL, scripts) — heavier than vanilla `slobac`, accepted as the cost of the locked-app trust property. Both manifests ship from day one so both harnesses are continuously exercised.

## Clean-room boundary, with a build-time provenance procedure

- **`claude-warehouse`** (third-party MIT): no code, no schema DDL, no unique ideas — ever. Claude Code support is reverse-engineered from the *harness's own* public on-disk format. Keeping `claude-warehouse` out of view is the *correct* posture, not a limitation.
- **`cursor-warehouse`** (operator's MIT): may be ported and relicensed to AGPLv3 — **but it is itself a port of `claude-warehouse`**, so without the upstream visible you cannot reliably tell which parts are genuinely original. The most portable pieces (the cross-harness engine: DuckDB/VSS, embedding/chunking, schema, watermark) are exactly the parts most likely to be upstream transliterations.
- **Operating procedure:** do not keep `cursor-warehouse` open by default, and do not copy from it speculatively. Reimplement cross-harness engine bits from the briefs/spike and first principles. When a specific piece would genuinely help, **request it from the operator**, who identifies what is genuinely original and therefore AGPL-able — in practice mostly the **torch work**. Schema is derived empirically regardless, which moots its provenance.
