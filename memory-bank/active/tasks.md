# Task: fix-plugin-env-heal-after-move (rework: hashed torch freeze)

* Task ID: fix-plugin-env-heal-after-move
* Complexity: Level 2
* Type: bug fix (rework)

Upgrade torch heal from **floating index URL** to a **machine-local hashed freeze** of the exact torch stack accepted at initialize/`make torch` time. Heal must replay that freeze with `--require-hashes` so plugin updates never pull a newer torch than the one that passed smoke.

## Design

| Piece | Choice |
| --- | --- |
| Project `uv.lock` | Stays torch-free (keep override). Do **not** pre-enumerate backends as extras. |
| Freeze artifact | `{stockroom_home}/torch-requirements.txt` — `uv pip compile --generate-hashes --emit-index-url` output for `torch==<installed.__version__>` against the chosen index |
| Sidecar metadata | `{stockroom_home}/torch-index` — the https index URL (human/debug + re-freeze input) |
| Freeze trigger | After **successful** `doctor smoke` (initialize); after `make torch` install; CLI `stockroom torch freeze --app-dir … --index …` |
| Heal | If torch missing: require freeze file → `uv pip install --no-config --directory APP_DIR --require-hashes -r torch-requirements.txt`. No freeze → soft-fail → `sr-initialize` / docs. **Never** floating `pip install torch --index` alone. |
| Failure | Yanked wheel / hash mismatch → soft-fail; operator re-runs initialize (pick → install → smoke → freeze) or manual path in `docs/torch.md` |
| Legacy | Index-only installs from prior rework: heal fails soft asking to freeze (no silent floating fallback) |

### Freeze algorithm (mechanism)

1. Assert `app_dir` venv can `import torch`; read `torch.__version__`.
2. Run (injectable runner):  
   `uv pip compile --generate-hashes --no-config --emit-index-url --default-index <index> -o <tmp> -` with stdin `torch==<version>`.
3. Atomically replace `{stockroom_home}/torch-requirements.txt`; write `torch-index`.

### Heal algorithm

1. Locked-deps ensure (unchanged, inexact).
2. If torch importable → noop.
3. Else if freeze file missing/invalid → failed (name `sr-initialize` / `docs/torch.md`).
4. Else `uv pip install --require-hashes -r freeze` into `app_dir`.

## Test Plan (TDD)

### Behaviors

- **F1 (freeze writes):** given venv with importable torch + index → `freeze_torch` writes requirements containing `torch==<version>`, `--hash=`, and index URL; writes `torch-index`
- **F2 (freeze refuses without torch):** no importable torch → failed/raises; no file written
- **F3 (heal from freeze):** torch missing + freeze present → install argv includes `--require-hashes` and `-r` freeze path; does **not** use bare `torch --index` without hashes
- **F4 (heal without freeze):** torch missing + no freeze → failed; no pip install
- **F5 (heal noop):** torch importable → noop even if freeze present
- **F6 (CLI freeze):** `stockroom torch freeze --app-dir … --index …` invokes freeze (stubbed compile runner)
- **F7 (writers):** `sr-initialize` documents freeze **after smoke**; `make torch` freezes after install; `docs/torch.md` covers manual freeze + failure remedy
- **Edge:** compile failure / timeout → soft-fail with reason; corrupt freeze file → heal soft-fail

### Test Infrastructure

- Framework: pytest under `skills/sr-search/tests/`
- Extend `test_torch_source.py`, `test_torch_cli.py`; update `test_engine_env.py` stubs
- Stub `uv pip compile` / `uv pip install` via injectable runner (no network in unit tests)
- Technology validation already done live: `uv pip compile --generate-hashes` for `torch==2.7.1+cpu` succeeded

## Implementation Plan

Each step: **tests first → implement → green**.

1. **Freeze API in `torch_source.py`**
   - Add `REQUIREMENTS_FILENAME = "torch-requirements.txt"`, `requirements_path()`, `freeze_torch(app_dir, index_url, *, runner=…)`, `read_freeze_path()`
   - Deprecate floating install path; keep `write_index` as sidecar writer used by freeze
   - Tests F1–F2, edges

2. **Heal uses freeze only**
   - Change `ensure_torch` / `_pip_install_cmd` to `--require-hashes -r <freeze>`
   - Remove heal-via-index-only behavior; update tests F3–F5; fix `test_engine_env` stubs

3. **CLI: `freeze` replaces `record` as primary**
   - `stockroom torch freeze --app-dir --index` (required)
   - Keep `record` as thin alias that errors with “use freeze” **or** remove `record` (prefer remove — unreleased)
   - Tests F6; dispatcher help fingerprint

4. **Writers onboard**
   - `sr-initialize`: after smoke success → `torch freeze` (not index-only record); order: install → smoke → freeze
   - `Makefile` `torch`: install then `torch freeze --app-dir … --index $(TORCH_INDEX)`
   - New `docs/torch.md`: contract, freeze location, heal, failure → re-initialize or manual freeze
   - Update `docs/development.md`, `docs/using.md`, `systemPatterns.md`, skill references that still say index-only

5. **Verification**
   - Targeted tests + full `make test` / lint

## Technology Validation

**PASS (live probe 2026-07-10):** `uv pip compile --generate-hashes --no-config --index-url https://download.pytorch.org/whl/cpu` for `torch==2.7.1+cpu` produced a hashed requirements file (torch + deps). Use `--emit-index-url` / `--default-index` in implementation so heal can resolve pytorch + PyPI deps.

No new dependencies.

## Dependencies

- Existing `uv` on PATH (`pip compile`, `pip install --require-hashes`)
- Prior work on branch: `ensure_engine_env`, rectify wiring, hook timeout 300 — retain
- Operator-agreed contract: freeze after smoke; heal replays freeze; failure → re-initialize or manual docs path

## Challenges & Mitigations

- **Freeze pins PyPI transitives (filelock, etc.) that also appear in `uv.lock`:** Install freeze **after** inexact deps sync; inexact sync won’t strip torch; minor version drift of shared deps is acceptable and documented in `docs/torch.md`.
- **Platform tags in hashed multi-wheel lines:** compile emits multiple hashes per package; `--require-hashes` install selects the matching wheel — rely on uv behavior (validated by integration smoke if needed).
- **Legacy index-only home:** no floating fallback; clear remedy to freeze once.
- **Compile needs network at freeze time:** only at initialize/`make torch`, not on every heal if wheels cached; heal still needs network if cache cold — same as today.
- **Not L3:** single subsystem extension of existing torch_source/ensure; design already agreed with operator.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [ ] Preflight
- [ ] Build
- [ ] QA
