---
task_id: cursor-model-ingest
complexity_level: 2
date: 2026-08-25
status: completed
---

# TASK ARCHIVE: cursor-model-ingest

## SUMMARY

Cursor `sessions.models` went empty after ~2026-08-20 because the WSL enrichment walker aborted the whole `/mnt` scan on a stale drive letter (`ENXIO` on `/mnt/i`) and never opened the live Windows `ai-code-tracking.db`. The tracking schema did not change. `_iter_dirs` now lists names then stats each child so one dead letter cannot hide sibling homes. Draft PR: [#121](https://github.com/Texarkanine/stockroom/pull/121).

## REQUIREMENTS

1. Diagnose the August 20 cutoff (guessed as a Cursor schema change).
2. Patch ingest only if Stockroom was the gap.
3. Keep reading the pre-change Cursor format (`ai_code_hashes` / `conversation_summaries`).
4. Do not invent a second format or change `messages.model` / `sessions.models` meaning.

## IMPLEMENTATION

Not a parser change. `_wsl_windows_candidate_paths` took an optional `mnt` (default `/mnt`). `_iter_dirs` uses `os.listdir` plus per-child `is_dir()` in its own `OSError` handler. `read_enrichment` SQL was left alone. One sentence in `docs/user-guide/load/sources.md`. After QA, a dead `Path.iterdir` monkeypatch was removed from the Users-listing test (walker never called it).

Key files: `skills/sr-search/src/stockroom/ingest/enrich.py`, `skills/sr-search/tests/test_ingest_enrich.py`, `docs/user-guide/load/sources.md`.

## TESTING

- TDD: five walker tests (`test_wsl_walker_*`) against the real walker (stale letter, unstatable user home, Users listing failure, missing mnt, drive without Users).
- Enrich + orchestrator 47/47; full engine **821 passed / 4 skipped**; dashboard JS 120 passed; ruff clean.
- Live WSL probe after the patch: `resolve_db_paths` returned the Linux sidecar and `/mnt/s/Users/Austin/.cursor/ai-tracking/ai-code-tracking.db`; this session mapped to `['grok-4.6']`.
- Preflight PASS (Gemini 3.1 Pro). QA PASS (Fable); docstring `stated` → `statted` only. LlamaPReview P2 on the dead iterdir mock: valid, then removed.

## LESSONS LEARNED

### Technical

Catching `OSError` around `Path.iterdir()` is not enough when the raise is a child's `is_dir()`. List names first, then stat. Transcript ingest stays on WSL `~/.cursor/`; only model enrichment is supposed to merge `/mnt/<drive>/Users/*/.cursor/…`.

### Process

A cutoff that looks like a vendor schema change can be a discovery walk that died. Probe the live sidecar and `resolve_db_paths()` before planning a parser.

### Million-dollar question

The walker would have been fail-soft per entry from the start. Pins and `STOCKROOM_AI_TRACKING_DB` stay escape hatches. That is what shipped.

## PROCESS IMPROVEMENTS

None — plan, preflight, build, QA, and reflect held. The schema-change guess was corrected in planning, not in build.

## TECHNICAL IMPROVEMENTS

Pre-existing and left alone: `_append_model` null/empty rows have no direct test; `mnt.is_dir()` at walker entry and `resolve_db_paths._add`'s `is_file()` are still unguarded if `/mnt` itself is unstatable.

## NEXT STEPS

Operator: one `stockroom ingest --full` to refill already-NULL Aug 20+ `models` (incremental ingest will not). Then finish [#121](https://github.com/Texarkanine/stockroom/pull/121).
