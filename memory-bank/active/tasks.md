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

1. **Orchestrator progress seam (ingest library)** — TDD cycle
   - Files: `skills/sr-search/tests/test_ingest_orchestrator.py`, then `skills/sr-search/src/stockroom/ingest/__init__.py`
   - Tests first: add failing cases that pass `on_progress=capture` and assert harness-start + `i/N` lines; assert default `on_progress=None` invokes nothing.
   - Then implement: optional `on_progress: Callable[[str], None] | None = None` on `ingest` and `_ingest_harness`. After selection, emit `{harness}: N sessions` (N = selected discovered conversations). In the selected loop, emit `{harness}: i/N sessions` (1-based over selected conversations). Default `None` = no calls.

2. **Ingest CLI `--verbose`** — TDD cycle
   - Files: `skills/sr-search/tests/test_ingest_cli.py`, then `skills/sr-search/src/stockroom/ingest/__main__.py`
   - Tests first: quiet `--full` stdout is summary-only (no `N/N` / mid-run progress); `--verbose --full` includes progress substrings plus `ingest complete:`; exit 0.
   - Then implement: `--verbose` flag; when set, pass `on_progress` that `print`s each line with `flush=True` (so long runs show live under pipes/tee). Keep end-of-run summary unconditional. Optional: elapsed seconds when verbose.

3. **Embed pipeline + CLI `--verbose`** — TDD cycle
   - Files: `skills/sr-search/tests/test_embed.py`, then `skills/sr-search/src/stockroom/embed.py`
   - Tests first: `embed_pending(..., on_progress=capture)` gets start + `i/N` lines; `embed.main([])` quiet (count only); `embed.main(["--verbose"], …)` shows progress + count; missing-warehouse + `--verbose` still exit 1 with existing hint.
   - Then implement: `on_progress` on `embed_pending`; `--verbose` on parser/`main` wiring `print(..., flush=True)`; preserve missing-warehouse path before encoder construction.

4. **Docs touch**
   - Files: `docs/development.md` (and CLI module docstrings if they list flags)
   - Changes: Mention `--verbose` on ingest/embed as optional progress output; keep brief.

5. **Verify**
   - Run targeted new/changed tests, then full `make test` / lint as required by build phase.

## Preflight Amendments

- Made TDD ordering explicit per implementable unit (tests before production code in steps 1–3).
- Progress printer uses `flush=True` so operators see lines immediately on long runs.

## Technology Validation

No new technology - validation not required

## Dependencies

- Existing argparse CLI patterns in `ingest/__main__.py` and `embed.py`
- Existing fixture roots / `warehouse_home` / `migrated_con` test fixtures
- No new packages

## Challenges & Mitigations

- **Denominator ambiguity (discovered vs selected vs written sessions including subagents):** Issue examples use session counts like `47/200`. Mitigation: use **selected discovered conversations** as `N` for the progress denominator (watermark-filtered work units); harness-start reports that same `N`. Subagent writes still happen inside each conversation without inflating `N` (or document if we count written NormalizedSessions instead — prefer discovered-selected for operator clarity).
- **Library printing vs injection:** Printing from deep library code would break quiet library callers and complicate tests. Mitigation: optional `on_progress` callback only; CLI is the sole default printer.
- **Subprocess vs in-process assertions for ingest progress:** Fixture ingest is fast; progress lines still appear. Mitigation: assert substrings in subprocess stdout; use orchestrator unit tests for precise line shapes.
- **Dispatcher / `stockroom ingest`:** Subcommand forwarding already passes argv through; no dispatcher change expected. Mitigation: if a packaging/help test pins exact help text, update it only if it fails.

## Pre-Mortem

- **Plan failed because progress was implemented only in CLI wrappers wrapping a silent library loop:** Would leave no way to unit-test progress without subprocess timing. Response: Step 1/3 already require library `on_progress` seams — keep that as the load-bearing design; CLI only wires the flag.
- **Plan failed because default runs became noisy and broke CI assertions on exact stdout:** Response: already covered by quiet-default behaviors and existing summary assertions; add explicit “no progress substring without `--verbose`” checks.
- **Plan failed by over-scoping elapsed time / watermark-skip stats into a redesign of IngestSummary:** Response: treat those as optional verbose-only print lines in CLI after the run, not schema/API changes to `IngestSummary`.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
