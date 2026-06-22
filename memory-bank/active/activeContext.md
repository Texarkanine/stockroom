# Active Context

## Resume Here

If you are picking this up in a fresh context window: read `planning/brainstorm/README.md` (decisions + open items + pipeline), then the four brainstorm bucket files. Everything decided so far is captured there.

## Current Position

**The brainstorm is finalized and committed** — the locked source of truth. All scope decisions are resolved **except the torch spike (O9)**, which the Tech Brief executes. No design document (PB/TB/Roadmap) has been written yet. No stockroom product code exists.

## Immediate Next Step

**Author the Product Brief** at `planning/product-brief.md`, from `planning/brainstorm/product.md`. Model it on the Niko `productContext` template (Target Audience / Use Cases / Key Benefits / Success Criteria / Key Constraints) but **more verbose**. This is the hard, high-value work. Verify with the operator before continuing.

## Then

1. **Author the Tech Brief** at `planning/tech-brief.md`, from `tech.md` + `implementation-details.md`, after the PB is solid. **Execute the torch spike (O9)** here — it is the one unresolved item and it gates embedding. Verify.
2. **Author the Roadmap** at `planning/roadmap.md`, from `roadmap.md`, after the TB is solid. Verify.
3. Retire the brainstorm; when build begins, promote the design docs into the persistent memory bank (`productContext` / `systemPatterns` / `techContext`).

## Key Constraints to Honor While Working

- **Faithful capture is the core principle (D19):** no truncation *at rest* of the fields we keep; truncation is a deliberate *read-time* feature (`sr-search` picks an appropriate level). Ingest is **ETL, not mirroring** — no verbatim raw layer, no tool outputs (inputs only). **Conversation reconstruction/linkage is first-class (D21)**; core fields are timestamp, full content, model-per-chain, subagent↔parent linkage, tool inputs, optional thinking, plus harness plan docs (D22).
- **v1 ingests both Cursor and Claude Code (D2/O12).** Claude Code is parsed **clean-room** from its native on-disk format — never by reusing `claude-warehouse` code or schema DDL.
- **O9 (torch) is the one open item** — an empirical uv spike, executed when authoring the Tech Brief.
- Build only in `/home/mobaxterm/git/stockroom` (fast WSL-internal); never the `Documents` mount.
- Run git with `--no-pager` and commit with `--no-gpg-sign`. Only commit when the operator asks.
- TDD and the other workspace rules apply once code work begins.
- Persistent memory-bank files (`productContext.md`, etc.) are intentionally **not yet created** — they are born from the verified PB/TB.
