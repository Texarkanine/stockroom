# Project Brief — Plan Stockroom

## Deliverable

Produce the founding planning documents for **stockroom**: a Product Brief, then a Tech Brief, then a Roadmap — each authored and verified in sequence, from a verified brainstorm that captures the operator's vision.

This memory bank's **active task is the planning effort itself**, not yet the build. It exists so the working context window can be closed and resumed at any step.

## What Stockroom Is

A local, AGPLv3, clean-room data warehouse for agentic-coding-harness conversations (Cursor in v1): ingest on-disk traces into DuckDB; search them (blended keyword+semantic, pure semantic, and raw SQL); visualize usage in a local dashboard; keep fresh via a nightly job; and survive schema changes via first-class, concurrency-safe migrations. Shipped as a `uv`-locked Python app inside a Cursor/Claude plugin skill.

## Source of Truth

`planning/brainstorm/` — start at `planning/brainstorm/README.md`, which holds the full **Decision Log (D1–D18)**, **Open Items (O1–O9)**, and the **document pipeline**. Do not re-derive decisions; read them there.

## Sequencing Rule

Each document is verified by the operator before the next is authored: **brainstorm → PB → TB → Roadmap.** The brainstorm is retired once the three design docs are solid.
