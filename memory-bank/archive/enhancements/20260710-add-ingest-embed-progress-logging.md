---
task_id: add-ingest-embed-progress-logging
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: add-ingest-embed-progress-logging

## SUMMARY

Added `--verbose` progress logging to `python -m stockroom.ingest` and `python -m stockroom.embed` so long runs show human-readable progress while staying quiet by default ([issue #1](https://github.com/Texarkanine/stockroom/issues/1)). Library surfaces take an optional `on_progress` callback; CLIs wire `print(..., flush=True)` only when `--verbose` is set. End-of-run summaries are preserved. Delivered with a clean build and QA pass.

## REQUIREMENTS

1. `--verbose` on both ingest and embed CLIs.
2. When verbose: harness/phase start lines and periodic or per-unit progress (e.g. `cursor: 47/200 sessions`).
3. Default (non-verbose) stays quiet mid-run for CI/tests.
4. Preserve existing end-of-run summaries (elapsed time optional/nice-to-have — deferred).
5. Extend CLI/orchestrator tests; suite stays green.

**Constraints:** Progress prints only with `--verbose`; no changes to ingest/embed correctness, watermarks, or encoding behavior; follow existing argparse/test patterns.

## IMPLEMENTATION

Optional `on_progress: Callable[[str], None] | None` on `ingest.ingest` and `embed_pending`; CLIs pass a flush-printing callback only when `--verbose`. Progress denominator = selected discovered conversations (ingest) / selected messages (embed). No shared progress module — thin duplicate wiring at two CLIs is fine. No `IngestSummary` API changes.

**Key files**

| Area | Files |
|------|--------|
| Ingest library | `skills/sr-search/src/stockroom/ingest/__init__.py` |
| Ingest CLI | `skills/sr-search/src/stockroom/ingest/__main__.py` |
| Embed | `skills/sr-search/src/stockroom/embed.py` |
| Tests | `tests/test_ingest_cli.py`, `tests/test_embed.py`, `tests/test_ingest_orchestrator.py` |
| Docs | `docs/development.md` |

## TESTING

- TDD: orchestrator callback → ingest CLI `--verbose` → embed pipeline/CLI `--verbose`.
- `make lint` clean; `make test` → **475 passed, 3 skipped**.
- `/niko-preflight` PASS (amendments: explicit TDD per unit; `flush=True`).
- `/niko-qa` PASS — no substantive findings; duplicate one-line `ProgressCallback` alias left as-is (shared module still YAGNI).

## LESSONS LEARNED

### Technical

What we built is the elegant form: library progress is an optional callback; CLIs opt in with `--verbose` and `flush=True`. No shared progress framework needed for two call sites. The seam matched existing `encoder_factory` injection style.

### Process

Nothing notable — plan sequence and file list were accurate; no surprises.

## PROCESS IMPROVEMENTS

None — Level 2 flow (plan → preflight → build → QA → reflect → archive) fit this enhancement cleanly.

## TECHNICAL IMPROVEMENTS

None required. A shared `ProgressCallback` alias module remains YAGNI unless a third call site appears.

## NEXT STEPS

- Optional follow-up: elapsed-time / watermark-skip stats as verbose-only CLI prints (deferred from this task).
- Close or annotate [issue #1](https://github.com/Texarkanine/stockroom/issues/1) as delivered.
