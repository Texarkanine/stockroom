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

The load-bearing packaging pattern. Lock everything hermetically with `uv lock --no-config`; exclude torch via an impossible environment-marker override (`override-dependencies = ["torch; python_full_version < '3'"]`) so it never enters the lock, then provision it per-machine out of band (`uv pip install torch --no-config --index <wheel-url>`). **After torch is installed, never run an exact sync** (`uv run --no-sync`, or `--inexact` when a sync is genuinely needed) — a bare sync deletes it. Local dev iteration (`make sync`, `make lock`, `make test`, etc.) is via the root [`Makefile`](../Makefile). Proven end-to-end in `planning/spikes/o9-torch/`; full rationale in tech-brief → "The Torch Exception".

## No truncation at rest; truncation is a read-time feature

Kept content (prompts, responses, tool inputs) is stored in full. Output truncation is applied only at read time (chiefly in `sr-search`), sized to answer without flooding the caller's context window. Storage-time caps are the failure mode stockroom exists to correct — do not reintroduce them.

## Harness-labeled schema, designed empirically

One shared set of tables (sessions, messages, tool_calls inputs-only, embeddings, `_sync_state`), every row carrying a `harness` column — never per-harness tables. Conversation reconstruction is first-class (conversation id, parent/child, ordering, subagent↔parent edge, model grain) atop a stable message-identity contract. Concrete DDL is derived test-first from real Cursor + Claude Code logs (the first Phase 1 task). (`plan_documents`, named in the original brief, was **dropped** during milestone-1 enumeration — no harness emits a plan-document record; `TodoWrite` lists already live in `tool_calls.tool_input`.)

## One meaning per field (cross-harness semantic uniformity)

**Every column means exactly one thing, independent of harness.** Only the *extraction* may differ per harness, and extraction MUST yield that one meaning. Never "`ordinal` is X for Cursor but Y for Claude" — that rots the moment a 3rd/4th harness lands. If a value cannot be made to mean the same thing everywhere, it does **not** get a shared column: it goes to a clearly-labeled `source_*` provenance column or is dropped. Identity is uniform by construction (`message_id = {session_id}#{ordinal}` for all harnesses, a deterministic surrogate; native ids like Claude's `uuid` are demoted to provenance, never joined on). Where a value is genuinely only available at a different grain per harness (e.g. model — per-message for Claude, per-conversation for Cursor), use **separate grain-specific columns** (`messages.model` vs `sessions.models`) and let each harness populate only the grain it actually has — the other is honestly NULL. We never fabricate or back-fill a grain we don't have.

## Typed columns for queryable data; JSON only for irreducible heterogeneity

DuckDB queries JSON (`->`, `->>`, `json_extract`) but **stores it as text (parsed per access) and has no JSON-path indexing** — it's a columnar engine that leans on full-scan + zonemaps, not indexes. So **never JSON-blob a value you want to filter, aggregate, or index.** First-class metrics get real typed columns (columnar, compressed, zonemapped, self-documenting): token usage is four `BIGINT` columns on `messages`, not a `usage` blob. Small sets use a native DuckDB `LIST` (`sessions.models` is `VARCHAR[]`), not JSON. JSON is reserved for the *one* irreducibly heterogeneous fidelity payload — `tool_calls.tool_input` (shape varies per tool, stored whole, never aggregated on internal keys).

## Thinking is not captured (by design)

We deliberately do **not** store model reasoning/"thinking". Rule: *if a harness lets us separate thinking from the response, we separate it and drop it; if it doesn't, we accept whatever is folded into `text`.* Claude emits explicit `thinking` blocks → dropped (we keep only `text`). Cursor has no separate thinking block → its single `text` channel is kept as-is. There is no `thinking` column, and there should never be one.

## Dual-manifest plugin, no build step, engine inside the `sr-search` skill

Ships from the `slobac` template as a `.cursor-plugin/plugin.json` + `.claude-plugin/plugin.json` over a shared `skills/` tree, **committed layout = install layout** (no build), versioned by release-please which syncs the version into both manifests. Both manifests ship from day one so both harnesses are continuously exercised.

**The full Python engine lives inside one real skill — `skills/sr-search/`** (`pyproject.toml`, `uv.lock`, `src/stockroom/`, `tests/`, and later migration SQL). This is heavier than vanilla `slobac` (whose app sits at repo root) and is the accepted cost of the locked-app trust property. `sr-search` (the core entrypoint) is the chosen host purely for coherence — resolution is plugin-root-relative (see next pattern), so the host dir is invisible to consumers. The engine project sets `[tool.uv] package = false` (run-in-place; deps locked, stockroom itself never built/installed), honoring no-build-step.

**Skeleton-skill convention:** a skill directory may ship before its behavior exists, carrying a `SKILL.md` with real front-matter and a body that states the dir's purpose and that the behavior is built in a named later phase. This is an honest placeholder, explicitly *not* a dummy — it is how the engine-bearing skill exists from Phase 0 while its search behavior lands in Phase 2.

## Cross-skill resource resolution (PLUGIN_ROOT, cribbed from `cursor-warehouse`)

`cursor-warehouse`'s own invention (safe to reuse — not `claude-warehouse`-derived). Sibling skills locate the shared engine **once on startup** via the harness-provided plugin-root env var (`CURSOR_PLUGIN_ROOT` in Cursor; the Claude equivalent — verify exact name empirically per harness at build), with a `find -L` fallback that traverses symlinked dev installs. Then invoke through the **torch-safe** contract — never an exact sync:

```bash
APP_DIR="${CURSOR_PLUGIN_ROOT:+$CURSOR_PLUGIN_ROOT/skills/sr-search}"
if [ -z "$APP_DIR" ] || [ ! -d "$APP_DIR" ]; then
  APP_DIR="$(dirname "$(find -L ~/.cursor/plugins -path '*/stockroom/*/skills/sr-search/pyproject.toml' 2>/dev/null | head -1)")"
fi
uv run --project "$APP_DIR" --no-sync python -m stockroom.<entrypoint> ...
```

## Layered licensing (REUSE/SPDX): AGPL on code, PPL-S on prompts

Intentional and load-bearing (mirrors `../slobac/REUSE.toml`). A root `REUSE.toml` + `LICENSES/*.txt`, enforced by `reuse lint` in CI/tests (not advisory). AGPLv3 is the **battle-tested explicit base on all code**; the experimental **PPL-S is layered over prompt-shaped content** (`skills/**` — `SKILL.md`, references), and code-shaped paths within `skills/**` (`*.py`, `*.sql`, `pyproject.toml`, `uv.lock`, `tests/**`) are **re-asserted AGPL**. Worst case prompts are still AGPL; best case they are PPL-S-clarified too. Relies on REUSE's last-matching-annotation-wins ordering: base AGPL → `skills/**` PPL-S → code-within-skills AGPL → vendored `.cursor/**` NOASSERTION.

## Clean-room boundary, with a build-time provenance procedure

- **`claude-warehouse`** (third-party MIT): no code, no schema DDL, no unique ideas — ever. Claude Code support is reverse-engineered from the *harness's own* public on-disk format. Keeping `claude-warehouse` out of view is the *correct* posture, not a limitation.
- **`cursor-warehouse`** (operator's MIT): may be ported and relicensed to AGPLv3 — **but it is itself a port of `claude-warehouse`**, so without the upstream visible you cannot reliably tell which parts are genuinely original. The most portable pieces (the cross-harness engine: DuckDB/VSS, embedding/chunking, schema, watermark) are exactly the parts most likely to be upstream transliterations.
- **Operating procedure:** do not keep `cursor-warehouse` open by default, and do not copy from it speculatively. Reimplement cross-harness engine bits from the briefs/spike and first principles. When a specific piece would genuinely help, **request it from the operator**, who identifies what is genuinely original and therefore AGPL-able — in practice mostly the **torch work**. Schema is derived empirically regardless, which moots its provenance.
