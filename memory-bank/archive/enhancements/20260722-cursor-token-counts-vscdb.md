---
task_id: cursor-token-counts-vscdb
complexity_level: 2
date: 2026-07-22
status: aborted
---

# TASK ARCHIVE: Cursor token counts from state.vscdb (ABORTED)

## SUMMARY

**This work was aborted and will not be merged.** Branch `enhance-cursor-tokens` explored enriching Cursor `sessions.*_tokens` from `state.vscdb` bubble `tokenCount` (enrich sidecar, session Σ, hybrid prefix/scan reads, XDG `[cursor].state_vscdb`). Live validation showed contemporary Cursor API token fills are **gone** (fields present as `{0,0}`; nonzero band ~2025-04 → ~2026-01, mostly composer-only). Nightly enrich is a dead product path. Operator disposition: **do not merge**; throw away branch code (including XDG config introduced here); keep learnings in this archive; punt Claude token ingest and [#82](https://github.com/Texarkanine/stockroom/issues/82) to separate follow-ups. Optional one-off historical backfill tracked as [#84](https://github.com/Texarkanine/stockroom/issues/84).

No prior Niko archive used `status: aborted` — this is intentional: the task completed its reflect/creative cycle, then the product premise was falsified and the implementation was discarded.

## REQUIREMENTS

Original goal (superseded):

1. Enrich Cursor IDE sessions from allowlisted bubble `tokenCount` in `state.vscdb` (session grain; messages NULL).
2. Fail-soft; no primary pivot; CLI unenriched from vscdb.
3. Practical I/O on WSL→Windows multi‑GB DB (hybrid prefix vs one `bubbleId:%` scan).

Final operator requirements at abort:

1. Do **not** ship Cursor vscdb token enrich in core/nightly ingest.
2. Do **not** merge `enhance-cursor-tokens`.
3. Schema dual-grain `*_tokens` / VIEW from prior work stay valuable for **Claude** (separate issue) — not justification for this branch.
4. XDG config on this branch is unused once enrich is abandoned — do not carry it forward from this branch’s merge; [#82] may recreate XDG later by reference only.

## IMPLEMENTATION

### What was built on the branch (discarded — reference only)

| Area | Notes |
|------|--------|
| `enrich_tokens.py` | `cursorDiskKV` preference; allowlist; session Σ apply; hybrid `full` / `SCAN_ID_THRESHOLD`; fail-soft |
| Orchestrator | Threaded `full=` into reader; IDE-only id set |
| Config | XDG `config.toml` `[cursor].state_vscdb`; env override |
| Docs / creatives | Ingest notes; grain/performance/legacy creatives; live schema scan dumps |

### Creative conclusion (inlined)

- **Contemporary tokens:** gone as a filled signal in vscdb — not relocated to another key family (scan: `ItemTable` / `cursorDiskKV` / `composerHeaders`; no billing/quota store).
- **Nightly enrich:** reject. **Full third-root ingest:** reject for core.
- **Optional one-off historical backfill:** [#84](https://github.com/Texarkanine/stockroom/issues/84) (finite corpus; not scheduled).
- **[#82](https://github.com/Texarkanine/stockroom/issues/82):** orthogonal (ai-tracking multi-DB / models cliff).

### Reflection (rework 3 — hybrid read; inlined)

Hybrid prefix/scan made `--full` practical vs N× prefix on 9p. Insight: correct for small `S` ≠ correct for `--full` on multi‑GB remote DB. Orchestrator fail-soft `except` hid `full=` spy TypeError. Later live product finding superseded the enrich goal entirely.

## TESTING

- Suite green for hybrid reader / orchestrator while the enrich path was still the plan (686 passed at last full run).
- Live smoke: warehouse Cursor session tokens mostly `(0,0)` or NULL; vscdb still had historical nonzero on non-joining composers; today’s composers all zero fills.
- `/niko-qa` PASS on rework 3; subsequent creative falsified the product premise → abort before merge.

## LESSONS LEARNED

- Validate that the **metering field is still populated for the traffic you care about** before investing in enrich I/O — join rate alone is insufficient.
- `cursorDiskKV` vs `ItemTable` and hybrid scan are real harness lessons if anyone builds [#84](https://github.com/Texarkanine/stockroom/issues/84); they are not reasons to keep dead enrich in core.
- Warehouse “outlives sources” and verbose `sessions` vs `messages` counts are easy to confuse during smoke tests.
- Aborting a reflected task needs an explicit archive status so future readers do not treat the branch as intended product.

## PROCESS IMPROVEMENTS

- Add an early “is the live field still nonzero for recent conversations?” gate before L2/L3 enrich builds against third-party IDE state DBs.
- When discarding a branch after archive, record **merge disposition** in the archive (merged / aborted / superseded) — first use of `status: aborted` here.

## TECHNICAL IMPROVEMENTS

- [#82](https://github.com/Texarkanine/stockroom/issues/82): walk/merge ai-tracking DBs; if XDG config is needed, **create it fresh** on that workstream — see `enhance-cursor-tokens` only as a discarded reference for XDG shape, not as a merge source.
- Claude message/session token ingest: **new stockroom issue** (keep schema; wire Claude parser → `*_tokens`).
- [#84](https://github.com/Texarkanine/stockroom/issues/84): optional one-shot historical vscdb backfill outside nightly core.

## NEXT STEPS

1. Leave `enhance-cursor-tokens` unmerged (operator may delete branch later).
2. Open/track Claude token ingest as its own issue if not already.
3. Next implementation workflow: [#82](https://github.com/Texarkanine/stockroom/issues/82) from a branch off main (or current trunk), creating XDG config only if that bug needs it — reference discarded branch for ideas, do not revive enrich.
4. [#84](https://github.com/Texarkanine/stockroom/issues/84) remains backlog enhancement.
