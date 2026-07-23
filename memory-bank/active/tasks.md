# Task: doctor-smoke-ensure-env-remedy

* Task ID: doctor-smoke-ensure-env-remedy
* Complexity: Level 2
* Type: simple enhancement
* Source: https://github.com/Texarkanine/stockroom/issues/86

When `stockroom doctor smoke` fails because torch is missing, recommend `stockroom shim ensure-env` if a usable hashed freeze already exists under stockroom home; otherwise keep the current `uv pip install` / `sr-initialize` remedy.

## Test Plan (TDD)

### Behaviors to Verify

- Freeze present + torch missing → `run_smoke` exits 1 with one stderr line that names `stockroom shim ensure-env` (and may still mention `sr-initialize` as re-pick); does **not** lead with the raw `uv pip install torch …` one-liner
- No freeze + torch missing → `run_smoke` exits 1 with one stderr line that still carries the literal `uv pip install torch --no-config --index … --directory <engine>` remedy (and/or `sr-initialize`) — current behavior
- Corrupt / unusable freeze (no `torch==` or no `--hash=`) + torch missing → same as no-freeze path (`read_freeze_path()` returns `None`)
- Encoder / wrong-width failures → unchanged re-pick remedy (regression)
- Happy path → unchanged exit 0 (regression)
- CLI torch-free smoke → still one stderr line; assertion branches on whether a usable freeze is present in the subprocess env (CI: no freeze → pip remedy; local torch-stripped+freeze → ensure-env)

### Test Infrastructure

- Framework: pytest (`skills/sr-search`)
- Test location: `skills/sr-search/tests/`
- Conventions: unit tests inject fakes into `run_smoke`; CLI tests subprocess `python -m stockroom.doctor`; torch home isolation via `STOCKROOM_HOME` + tmp dir (see `test_torch_source.py`'s `stockroom_home` fixture pattern)
- New test files: none — extend `test_doctor.py` and adjust `test_doctor_cli.py`

## Implementation Plan

1. **Failing tests for freeze-aware missing-torch remedy (unit + CLI)**
   - Files: `skills/sr-search/tests/test_doctor.py`, `skills/sr-search/tests/test_doctor_cli.py`
   - Changes:
     - Add a local `stockroom_home` fixture in `test_doctor.py`; split/replace `test_smoke_torch_missing_is_ratcheted_diagnosis` into no-freeze (current pip/`--directory` remedy), usable-freeze (`shim ensure-env`, no leading raw pip), and unusable-freeze (falls through to pip/`sr-initialize`)
     - Update `test_smoke_torch_free_env_fails_loudly_with_remedy` to branch on `torch_source.read_freeze_path()` (ensure-env vs pip remedy)
   - Run: freeze-present unit case(s) must fail before production code changes

2. **Implement freeze-aware remedy in `run_smoke`**
   - Files: `skills/sr-search/src/stockroom/doctor.py`
   - Changes: on torch import failure, call `torch_source.read_freeze_path()` (same usability gate as `ensure_torch` / `shim ensure-env`). If not `None`, remedy recommends `stockroom shim ensure-env` and may mention `sr-initialize` for re-pick; if `None`, keep existing `uv pip install …` + `sr-initialize` text. Update module/`run_smoke` docstrings for the errmsg ratchet.
   - Do **not** invent a parallel freeze check — reuse `read_freeze_path()`.
   - Run: previously failing tests pass; encoder/happy-path regressions still green

3. **Docs alignment (small)**
   - Files: `docs/user-guide/troubleshooting/torch.md`
   - Changes: under missing-torch guidance, note that `doctor smoke`'s missing-torch diagnosis recommends `stockroom shim ensure-env` when a freeze exists (mirrors the existing semantic-failure bullet). Keep brief; no redesign of the page.

4. **Verify**
   - Run targeted doctor tests, then full suite per project norms.

## Preflight Amendments

- Reordered CLI test update into step 1 so every implementable unit is test-before-code (TDD plan encoding).

## Technology Validation

No new technology - validation not required

## Dependencies

- `stockroom.torch_source.read_freeze_path` (existing)
- `stockroom.shim.ensure-env` / `ensure_torch` heal path (existing; message only)
- Existing doctor unit/CLI test harness

## Challenges & Mitigations

- **CLI test env variance (CI torch-free vs local freeze-without-torch):** Branch assertions on `read_freeze_path()` rather than hard-coding one remedy string.
- **Issue wording vs heal gate (`requirements` + `index` vs hashed freeze alone):** Prefer `read_freeze_path()` — that is what `ensure_torch` actually gates on; index is already baked into a proper freeze. Document this decision in progress notes.
- **Accidental import weight in doctor:** `torch_source` is already a light home/path helper used by shim; importing it from doctor is consistent with the heal surface. Avoid importing shim CLI.

## Pre-Mortem

- **Wrong freeze predicate (e.g. file-exists only, or requiring index sidecar) causes false ensure-env suggestions that then soft-fail:** already covered by Challenge 2 — use `read_freeze_path()` only.
- **Plan over-scopes into changing `ensure_torch` / provisioning UX:** cut scope — message-only change in `run_smoke` + tests + one troubleshooting note.
- **Unit tests share real STOCKROOM_HOME and flake across machines:** isolate with monkeypatched `STOCKROOM_HOME` in doctor unit tests (same pattern as torch tests).

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
