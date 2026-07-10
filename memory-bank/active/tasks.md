# Task: add-ingest-embed-progress-logging

* Task ID: add-ingest-embed-progress-logging
* Complexity: Level 2
* Type: simple enhancement

Add `--verbose` progress logging to `python -m stockroom.ingest` and `python -m stockroom.embed` so long runs show human-readable progress while staying quiet by default ([issue #1](https://github.com/Texarkanine/stockroom/issues/1)).

## Test Plan (TDD)

### Behaviors to Verify

- Ingest quiet default: `python -m stockroom.ingest --full` (no `--verbose`) → stdout is only the existing end-of-run summary (`ingest complete:` / per-harness counts); no mid-run progress lines
- Ingest verbose harness start: `… --full --verbose` → before/during the run, stdout includes a harness-start line naming the harness and discovered session count (e.g. contains `cursor` and a session count)
- Ingest verbose per-session progress: with fixtures that yield multiple sessions, `--verbose` → stdout includes at least one `N/M` style progress line for a harness
- Ingest verbose preserves summary: `--verbose` still ends with the existing `ingest complete:` summary; exit 0
- Embed quiet default: `embed.main([])` with seeded warehouse → stdout is only the existing `embedded N chunk vector(s)` line; no mid-run progress
- Embed verbose progress: `embed.main(["--verbose"], …)` with multiple pending messages → stdout includes progress (pending total and/or `N/M` style) plus the final count line; exit 0
- Embed verbose missing warehouse: `embed.main(["--verbose"])` with no warehouse → still exit 1 with the existing stderr hint (verbosity does not change the friendly error path)
- Orchestrator callback no-op: `ingest.ingest(..., on_progress=None)` (default) → no prints / no callback invocations required; existing orchestrator tests unchanged in behavior
- Orchestrator callback fires: `ingest.ingest(..., on_progress=capture)` → capture receives harness-start and per-session lines matching selected work
- Edge — empty harness: discover yields nothing → no crash; verbose may omit progress or emit a zero/skip start line; summary still prints
- Edge — argparse: `--verbose` is accepted by both CLIs (`--help` lists it); unknown flags still rejected

### Test Infrastructure

- Framework: pytest (configured in `skills/sr-search/pyproject.toml`)
- Test location: `skills/sr-search/tests/`
- Conventions: CLI smoke via real subprocess (`test_ingest_cli.py`); embed CLI via in-process `embed.main` + `capsys` (`test_embed.py`); orchestrator via injected connection (`test_ingest_orchestrator.py`)
- New test files: none — extend `test_ingest_cli.py`, `test_embed.py`, and `test_ingest_orchestrator.py`

## Implementation Plan

1. [x] **Orchestrator progress seam (ingest library)** — TDD cycle
2. [x] **Ingest CLI `--verbose`** — TDD cycle
3. [x] **Embed pipeline + CLI `--verbose`** — TDD cycle
4. [x] **Docs touch**
5. [x] **Verify** — `make lint` clean; `make test` → 475 passed, 3 skipped

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing argparse CLI patterns in `ingest/__main__.py` and `embed.py`
- Existing fixture roots / `warehouse_home` / `migrated_con` test fixtures
- No new packages

## Challenges & Mitigations

- **Denominator ambiguity:** Progress `N` = selected discovered conversations (ingest) / selected messages (embed).
- **Library printing vs injection:** Optional `on_progress` callback; CLI wires `print(..., flush=True)`.
- **Subprocess vs in-process:** Covered by both CLI and orchestrator/unit tests.

## Pre-Mortem

- CLI-only wrapping without library seam — avoided via `on_progress`.
- Noisy default breaking CI — quiet-default tests added.
- Over-scoping `IngestSummary` — not done; elapsed/skip stats deferred.

## Preflight Amendments

- Made TDD ordering explicit per implementable unit (tests before production code in steps 1–3).
- Progress printer uses `flush=True` so operators see lines immediately on long runs.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
