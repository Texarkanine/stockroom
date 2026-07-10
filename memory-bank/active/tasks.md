# Task: fix-plugin-env-heal-after-move (rework: torch source persistence)

* Task ID: fix-plugin-env-heal-after-move
* Complexity: Level 2
* Type: bug fix (rework)

Persist the per-machine torch wheel index under stockroom home and reinstall torch during `ensure_engine_env` when the engine venv lacks torch but a recorded index exists — so plugin updates do not silently break overnight embed / semantic.

## Design

| Piece | Choice |
| --- | --- |
| Record location | `{stockroom_home}/torch-index` (one URL line); same home as warehouse via `warehouse.resolve_home` / `home_dir` |
| Write | `stockroom torch record --index URL`; called from `sr-initialize` after guided install and from `make torch` |
| Heal | After locked-deps ensure: if venv cannot `import torch` and record exists → `uv pip install torch --no-config --directory APP_DIR --index URL`; if missing and no record → soft-fail reason naming `sr-initialize` |
| Guessing | Never invent an index |
| Hook timeout | Raise to 300s (torch wheels are large); ensure torch subprocess timeout bounded (~240s) |

## Test Plan (TDD)

- **T1:** `write_index` / `read_index` round-trip under tmp `STOCKROOM_HOME`
- **T2:** `ensure_torch` noops when torch importable in venv
- **T3:** `ensure_torch` runs `uv pip install … --index <recorded>` when torch missing + record present
- **T4:** `ensure_torch` soft-fails (no pip) when torch missing + no record
- **T5:** `ensure_engine_env` invokes torch ensure after deps heal
- **T6:** CLI `torch record` writes the file; help documents it
- **T7:** Makefile `torch` target records `TORCH_INDEX` after pip install
- **Edge:** invalid/empty index file → soft-fail; relative path rejected or absolutized as URL only

## Implementation Plan

Each step: tests first → implement → green.

1. `stockroom/torch_source.py` — path, read, write, ensure_torch (injectable runners)
2. Wire into `ensure_engine_env`
3. CLI `stockroom torch record` (+ dispatcher entry)
4. `sr-initialize` Step 5 records index after install; docs
5. `Makefile` torch target records; hook timeout 300; packaging tests
6. Full suite

## Technology Validation

No new technology — validation not required.

## Challenges & Mitigations

- **Hook timeout vs torch download:** 300s budget; soft-fail + retry next session/ensure if killed mid-download.
- **Self-managed torch without record:** cannot heal; remedy is `torch record` once or re-run initialize — document.
- **doctor stays read-only:** record/ensure live outside doctor.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
