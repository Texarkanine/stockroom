# Product Context

**Authoritative source (until the end-of-roadmap cut): [`planning/product-brief.md`](../planning/product-brief.md).**

This file is a deliberately thin pointer during the v1 build. Per the agreed memory-bank strategy, the rich planning docs (`product-brief.md`, `tech-brief.md`, `roadmap.md`) remain the grounding truth throughout the roadmap. The durable product context is distilled into the sections below as the **final roadmap step**; the planning docs are then discarded and this file becomes the standalone grounding truth. **Cut gate:** before the planning docs are deleted, `memory-bank/` must contain zero references to `planning/`.

Orientation: Stockroom turns a power user's agentic-coding history (Cursor + Claude Code) into a local, private, fully-searchable single-file DuckDB warehouse, exposed through a few intuitively-named skills — blended search, semantic search, raw SQL, and an at-a-glance dashboard. Its defining promise is **fidelity**: kept content is stored whole, never truncated at rest. It is personal-first software held to a publishable, supply-chain-safe (locked-dependency, local-only, AGPLv3) standard.

## Target Audience

Privacy- and supply-chain-conscious power users of agentic coding harnesses, on heterogeneous machines (real WSL/Windows-mount contingent). See product-brief → "Target Audience".

## Use Cases

Find/recall past conversations (keyword, meaning, raw SQL), see activity at a glance, stay fresh automatically, survive schema upgrades. See product-brief → "Use Cases".

## Key Benefits

Faithful recall (no truncation at rest), local & private, supply-chain safe, doesn't-break-your-data migrations, clean-room AGPLv3 provenance, harness-extensible. See product-brief → "Key Benefits".

## Success Criteria

Installs and self-configures (`sr-initialize`); ingests both Cursor and Claude Code; all four surfaces work; kept content is complete; survives a schema-changing upgrade under concurrent load; good enough to live in, clean enough to ship. See product-brief → "Success Criteria".

## Key Constraints

No truncation at rest; local-only/no-telemetry/no-cloud; AGPLv3; clean-room w.r.t. `claude-warehouse`; uv-locked except torch; both harnesses from day one; hook discipline. See product-brief → "Key Constraints".
