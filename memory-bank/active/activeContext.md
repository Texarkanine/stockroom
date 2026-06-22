# Active Context

## Resume Here

If you are picking this up in a fresh context window: read `planning/product-brief.md` (operator-verified) and `planning/tech-brief.md` (authored, **awaiting operator verification**), with `planning/brainstorm/README.md` as the locked decision log. The next planning doc is the Roadmap, sourced from `planning/brainstorm/roadmap.md`.

## Current Position

**The Product Brief and Tech Brief are both authored** — `planning/product-brief.md` (verified) and `planning/tech-brief.md` (awaiting verification). The brainstorm remains the locked source of truth for scope decisions. **All open items are now resolved, including the torch spike (O9)** — see below. No Roadmap yet. No stockroom product code exists.

## Immediate Next Step

**Operator verifies the Tech Brief.** Once verified, **author the Roadmap** at `planning/roadmap.md` from `planning/brainstorm/roadmap.md`.

## Decisions Made While Authoring the Tech Brief

- **O9 (torch) RESOLVED empirically.** Mechanism — "lock everything except torch":
  - Exclude torch from the lock: `[tool.uv] override-dependencies = ["torch; python_full_version < '3'"]` (impossible marker; `requires-python` ≥ 3.11).
  - Generate the lock hermetically: `uv lock --no-config` (the operator's ambient user-level pytorch index leaks into resolution otherwise).
  - Provision torch out-of-band: `uv pip install torch --no-config --index <platform-url>` (`--no-config` is required to bypass the override; explicit `--index` picks the accelerator build).
  - Never run an exact `uv sync` afterward (it uninstalls torch). Runtime uses `uv run --no-sync` or `uv sync/run --inexact`.
  - Proven end-to-end on GPU **and** CPU. Reproducible artifact at `planning/spikes/o9-torch/` (`pyproject.toml` + hermetic `uv.lock` + `smoke.py`). Hardware note: PyPI's default torch dropped Pascal `sm_61`; the cu126/2.11 wheel works on the GTX 1070 — concrete proof torch must be a per-machine, smoke-tested choice in `sr-initialize`.
- **Schema scope for the TB = design-level** (operator decision). The TB fixes the schema **design and contract**; the side-by-side real-log field enumeration + the locked table DDL are the **first Phase 1 build task**, done test-first. Resolved a genuine conflict in the source docs (README said the TB "locks the schema"; roadmap/impl-details place enumeration in build).

## Then

1. Retire the brainstorm once PB / TB / Roadmap are all verified.
2. When build begins, promote the design docs into the persistent memory bank (`productContext` / `systemPatterns` / `techContext`). The first build task is the schema/ingest enumeration (see TB → The Conversation Schema).

## Key Constraints to Honor While Working

- **Faithful capture is the core principle (D19):** no truncation *at rest* of the fields we keep; truncation is a deliberate *read-time* feature (`sr-search` picks an appropriate level). Ingest is **ETL, not mirroring** — no verbatim raw layer, no tool outputs (inputs only). **Conversation reconstruction/linkage is first-class (D21)**; core fields are timestamp, full content, model-per-chain, subagent↔parent linkage, tool inputs, optional thinking, plus harness plan docs (D22).
- **v1 ingests both Cursor and Claude Code (D2/O12).** Claude Code is parsed **clean-room** from its native on-disk format — never by reusing `claude-warehouse` code or schema DDL.
- **O9 (torch) is resolved** — recipe captured above and in the TB; the `planning/spikes/o9-torch/` artifact is reproducible.
- Build only in `/home/mobaxterm/git/stockroom` (fast WSL-internal); never the `Documents` mount.
- Run git with `--no-pager` and commit with `--no-gpg-sign`. Only commit when the operator asks.
- TDD and the other workspace rules apply once code work begins.
- Persistent memory-bank files (`productContext.md`, etc.) are intentionally **not yet created** — they are born from the verified PB/TB.
