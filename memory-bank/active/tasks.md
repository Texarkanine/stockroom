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

1. **Orchestrator progress seam (ingest library)**
   - Files: `skills/sr-search/src/stockroom/ingest/__init__.py`, `skills/sr-search/tests/test_ingest_orchestrator.py`
   - Changes: Add optional `on_progress: Callable[[str], None] | None = None` to `ingest` and `_ingest_harness`. After discovery/selection, call with a harness-start line (`{harness}: N sessions` using selected count as the work unit, or discovered + selected if useful). In the write loop, call with `{harness}: i/N sessions` (1-based `i` over selected conversations, or over written sessions — pick one consistent denominator and document in the callback message). Default `None` = no calls. Write failing orchestrator tests first that capture callback lines.

2. **Ingest CLI `--verbose`**
   - Files: `skills/sr-search/src/stockroom/ingest/__main__.py`, `skills/sr-search/tests/test_ingest_cli.py`
   - Changes: Add `--verbose` flag. When set, pass `on_progress=print` (or a thin wrapper) into `ingest.ingest`. Keep end-of-run summary unconditional. Optionally print elapsed seconds when verbose (nice-to-have). Tests: quiet default has no mid-run lines; verbose has progress + summary.

3. **Embed pipeline progress seam**
   - Files: `skills/sr-search/src/stockroom/embed.py`, `skills/sr-search/tests/test_embed.py`
   - Changes: Add optional `on_progress` to `embed_pending` (same `Callable[[str], None] | None` shape). After selecting messages, report pending count; in the per-message loop, report `embed: i/N messages` (or equivalent). Wire `--verbose` on `_build_parser` / `main` to pass `print` when set. Preserve missing-warehouse path before encoder construction. Tests for quiet vs verbose CLI output.

4. **Docs touch**
   - Files: `docs/development.md` (and module docstrings on the CLI entrypoints if they list flags)
   - Changes: Mention `--verbose` on ingest/embed as optional progress output; keep brief.

5. **Verify**
   - Run targeted new/changed tests, then full `make test` / lint as required by build phase.

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
- [ ] Preflight
- [ ] Build
- [ ] QA
