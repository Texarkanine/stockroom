# Task: torch-failures-help

* Task ID: torch-failures-help
* Complexity: Level 2
* Type: simple enhancement

Rework of the open pull request. When `import torch` fails and a usable hashed freeze exists, `stockroom semantic` and `stockroom embed` run `ensure_engine_env` once, print that the restore is in progress, and retry the encoder once. If the restore fails, or the retry still fails, stderr names that failure and `sr-initialize`, and does not tell anyone to run `stockroom shim ensure-env` again.

No usable freeze stays an interruption. The next step is `sr-initialize`. The line does not contain `uv pip install` or a literal `<build>`. An encoder exception after torch imports stays an interruption. The line names the exception and `sr-initialize`. It does not say the wheel is wrong, and nothing installs a different wheel.

`doctor smoke` stays report-only. It does not call `ensure_engine_env`. Its missing-torch-plus-freeze line still names `stockroom shim ensure-env`. Its no-freeze line drops the pip template and names `sr-initialize`, same as the commands.

The open pull request is updated when this rework is pushed.

## Test Plan (TDD)

### Behaviors to Verify

- [semantic restores and retries]: usable freeze, `encoder_factory` raises `ModuleNotFoundError` named `torch` once and then returns `FakeEncoder`, injected healer returns `EnsureReport(action="synced")` → healer called once with the engine directory, exit `0`, stderr contains `restoring torch from the hashed freeze`, stderr does not contain `ensure-env`, no traceback
- [semantic restore fails]: usable freeze, factory always raises that `ModuleNotFoundError`, healer returns `action="failed"` and `reason="hash mismatch"` → exit `1`, healer called once, factory called once, stderr contains `hash mismatch` and `sr-initialize`, and does not contain `ensure-env`
- [semantic retry still fails]: usable freeze, healer returns `synced`, factory raises the torch `ModuleNotFoundError` on both calls → exit `1`, factory called twice, stderr contains the restoring line, the second failure, and `sr-initialize`, and does not contain `ensure-env`
- [semantic, no freeze]: no usable freeze, factory raises the torch `ModuleNotFoundError` → healer is not called, exit `1`, stderr contains `sr-initialize`, and does not contain `uv pip install`, `<build>`, or `ensure-env`
- [semantic, unusable freeze]: freeze file with no `--hash=` line, same factory → same outcome as no freeze
- [semantic, encoder exception]: factory raises `OSError("model download failed")` → healer is not called, exit `1`, stderr contains `OSError`, `model download failed`, and `sr-initialize`, and does not contain `wheel index` or `ensure-env`
- [semantic, other import]: factory raises `ModuleNotFoundError` named `sentence_transformers` → the exception propagates, healer is not called
- [embed restores and retries]: same success shape as semantic, through `embed.main`
- [embed restore fails]: same failed-restore shape as semantic, through `embed.main`
- [embed, no freeze]: healer not called, exit `1`, `sr-initialize` present, `uv pip install` and `<build>` absent
- [embed, encoder exception]: healer not called, exception text and `sr-initialize` present, `wheel index` absent
- [embed, other import]: `sentence_transformers` propagates, healer not called
- [doctor smoke, no freeze]: existing smoke test, no healer injection → exit `1`, one stderr line, `sr-initialize` present, `uv pip install` and `<build>` absent, `ensure-env` absent
- [doctor smoke, unusable freeze]: same as no freeze
- [doctor smoke, usable freeze]: still one line containing `stockroom shim ensure-env`, and the test does not install torch
- [doctor smoke, encoder exception]: exception text and `sr-initialize` present, `wheel index` absent

### Test Infrastructure

- Framework: pytest, `-n0` while iterating on these files
- Test location: `skills/sr-search/tests/`
- Conventions: `encoder_factory` injection, `warehouse_home` / `stockroom_home`, `capsys`, docstrings state the behavior
- New test files: none

## Implementation Plan

### 1. Restore from the freeze, and stop naming a repair we do not have — executable

- Files: `skills/sr-search/src/stockroom/embed.py`, `skills/sr-search/src/stockroom/semantic.py`, `skills/sr-search/src/stockroom/doctor.py`, `skills/sr-search/tests/test_semantic.py`, `skills/sr-search/tests/test_embed.py`, `skills/sr-search/tests/test_doctor.py`, `skills/sr-search/tests/test_doctor_cli.py`

1. Stub tests: add empty `test_cli_torch_missing_with_freeze_restores_and_retries`, `test_cli_torch_restore_failure_names_reason`, and `test_cli_torch_restore_retry_still_fails` in `test_semantic.py` and `test_embed.py`. Rewrite `test_cli_torch_missing_without_freeze_names_pip_remedy`, `test_cli_torch_missing_with_unusable_freeze_names_pip_remedy`, and `test_cli_encoder_load_failure_names_repick` in `test_semantic.py` to the behaviors above. Delete `test_cli_torch_remedy_quotes_engine_path` (it locks the pip command this rework removes). Rewrite the matching embed tests, including replacing `test_cli_torch_missing_with_freeze_names_ensure_env`. Rewrite `test_smoke_torch_missing_without_freeze_names_pip_remedy`, `test_smoke_torch_missing_with_unusable_freeze_falls_through_to_pip`, and `test_smoke_encoder_failure_names_error_and_next_action` in `test_doctor.py`. Delete `test_smoke_remedy_command_takes_the_engine_path_as_one_word`. Rewrite `test_smoke_torch_free_env_fails_loudly_with_remedy` in `test_doctor_cli.py`.
2. Stub interface: in `embed.py`, add `start_encoder(factory, *, healer=None) -> Encoder | None` with a docstring and `return None`. Add `healer: Callable[[Path], EnsureReport] | None = None` to `semantic.main` and `embed.main`.
3. Write tests and run red: fill the stubs. Freeze tests that restore pass a fake healer and a factory with a call counter. Assert the healer is not called unless the exception is a missing `torch` and `read_freeze_path()` is not `None`. Run the new and rewritten tests and confirm they fail.
4. Write code and run green: `start_encoder` tries `factory()` once. On a torch `ModuleNotFoundError` with a usable freeze, it prints `restoring torch from the hashed freeze` to stderr, calls `healer` or `ensure_engine_env` once with `default_app_dir()`, and on `action="synced"` tries `factory()` one more time. A failed report prints `error: torch restore failed ({reason}) — re-run sr-initialize` and returns `None`. A second construction failure prints `error: encoder check failed ({type}: {exc}) — re-run sr-initialize` and returns `None`. No freeze prints `error: torch is not installed in the engine environment at {app_dir} — re-run sr-initialize (install → smoke → freeze)`. Any other `ModuleNotFoundError` propagates. Any other exception prints the encoder-check line above, with no wheel claim. `missing_torch_remedy` keeps the ensure-env clause for a usable freeze, and its no-freeze clause becomes the `sr-initialize` sentence. `encoder_load_remedy` becomes `re-run sr-initialize`. `doctor.run_smoke` stays on those two functions and does not gain a healer. Both mains use `start_encoder` and return `1` when it returns `None`. Run these tests, then `test_doctor.py` and `test_doctor_cli.py`.

### 2. Agent text and the torch page — prose/policy

- Files: `skills/sr-semantic/SKILL.md`, `skills/sr-search/references/system-model.md`, `docs/user-guide/troubleshooting/torch.md`, `docs/user-guide/load/basic.md`
- No tests: prose/policy artifact

1. In `skills/sr-semantic/SKILL.md`, the missing-torch row says the command restores torch from a usable freeze and retries. A restore failure, or no usable freeze, says re-run `sr-initialize`. Do not tell the agent to run `stockroom shim ensure-env` for that row. The encoder-failure row names `sr-initialize` and does not say the wheel is wrong.
2. In `system-model.md`, replace the three-way "print a command" sentence with the same behavior.
3. In `torch.md`, the semantic/embed section says the command restores from a usable freeze. No freeze, and a failed restore, say `sr-initialize`. Remove the `uv pip install` template. The doctor section still says smoke names `stockroom shim ensure-env` when a freeze exists and does not install it.
4. In `basic.md`, say a missing torch with a freeze is restored by the command. `sr-initialize` is the step when that restore does not happen.

## Technology Validation

No new technology - validation not required

## Dependencies

- `stockroom.engine_env.ensure_engine_env` and `EnsureReport`
- `stockroom.torch_source.read_freeze_path`
- `stockroom.shim.default_app_dir`

## Challenges & Mitigations

- A test that writes a real freeze must not call the real healer. `uv pip install` of torch is the production default. Tests pass a fake, and the production default is used only when `healer` is omitted.
- A successful restore that still cannot build the encoder must not heal again. `start_encoder` retries `factory()` once.
- `doctor smoke` must keep reporting a missing torch. It does not receive a healer. Its usable-freeze test still expects the ensure-env words and does not install.
- The restoring line plus a failure line is two stderr lines. The one-line rule remains for doctor smoke and for failures that do not attempt a restore.

## Pre-Mortem

- Healing from inside `doctor smoke` would erase the condition smoke exists to show. The plan leaves smoke report-only.
- Calling the healer whenever a freeze exists, including on an encoder `OSError`, would reinstall a bad wheel. The healer runs only for a torch `ModuleNotFoundError`.
- Leaving the `<build>` pip line in `missing_torch_remedy` would keep a command that cannot be run. The no-freeze clause changes, and the quoting tests that lock that command are deleted.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [x] QA

## QA Results

PASS WITH ADVISORY (see `memory-bank/active/.qa-validation-status`). All planned behaviors are implemented and test-pinned; the four touched test files pass (100 passed, 4 torch-gated skips), neighboring suites pass, ruff check and format are clean. Three non-blocking advisories: a "stays read-only" clause in `system-model.md` that does not fit embed's read-write connection, duplicated test helpers across `test_semantic.py`/`test_embed.py` (matches suite convention), and the plan's stub list naming `test_cli_torch_restore_retry_still_fails` for both CLI files while the behaviors checklist requires it only for semantic. No build or plan rerun required.
