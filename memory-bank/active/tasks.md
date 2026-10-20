# Task: torch-failures-help

* Task ID: torch-failures-help
* Complexity: Level 2
* Type: simple enhancement

`stockroom semantic` and `stockroom embed` print a raw traceback when torch cannot be imported or the encoder cannot be built. The skill an agent follows then says not to retry and to re-run `sr-initialize`, so the agent never runs `stockroom shim ensure-env`.

The goal, without naming a means: the next run that cannot use torch exits non-zero with one stderr line whose command fixes that specific failure, and the skill does not send the agent to a heavier or wrong command.

The ticket's option 1 (ensure-env when a freeze exists, otherwise `sr-initialize`, for every encoder failure) is not optimal. `doctor smoke` already splits three ways, and the third way matters: an encoder that raises after torch imports is a bad wheel, and `stockroom shim ensure-env` would reinstall that same wheel from the freeze. Option 2 alone leaves the traceback, which breaks the skill's own rule that each failure is a clean stderr line, and humans never open the skill. Option 3 (a new doctor command) does not help: the agent never ran doctor. Catching inside `BgeEncoder.__init__` is the wrong layer: `doctor smoke` and the live encoder tests expect the raw exception from construction.

Decision: one pair of remedy strings, owned next to the encoder, used by `doctor smoke` and by both CLIs. Only `ModuleNotFoundError` for `torch` (or `torch.*`) takes the missing-import branch (usable freeze → `stockroom shim ensure-env`; otherwise the quoted `uv pip install` line). Any other exception from `encoder_factory()` takes the re-pick branch. Any other `ModuleNotFoundError` propagates. The skill, the torch-contract sentence, and the two disagreeing headings in the torch troubleshooting page say the same split. `sr-search` gets no new error table; it already defers to `sr-semantic`.

## Test Plan (TDD)

### Behaviors to Verify

- [semantic, torch missing, no usable freeze]: `semantic.main` with a query, a warehouse file, and an `encoder_factory` that raises `ModuleNotFoundError` named `torch`, and no usable freeze under `STOCKROOM_HOME` → exit `1`, exactly one stderr line, no `Traceback`, the line contains `error: torch is not installed in the engine environment at`, the literal `uv pip install torch --no-config --index`, and `--directory` plus the shell-quoted engine path; the line does not contain `ensure-env`
- [semantic, torch missing, usable freeze]: same call after a hashed `torch-requirements.txt` (a `torch==` pin and a `--hash=` line) → exit `1`, one stderr line containing `stockroom shim ensure-env`, and not `uv pip install torch`
- [semantic, torch missing, unusable freeze]: a freeze file with no `--hash=` line → the pip line, not `ensure-env`
- [semantic, encoder load failure]: `encoder_factory` raises `OSError("model download failed")` → exit `1`, one stderr line containing `encoder check failed`, `OSError`, `model download failed`, and `sr-initialize`, and not `ensure-env`
- [semantic, other import error]: `encoder_factory` raises `ModuleNotFoundError` named `sentence_transformers` → the exception propagates
- [semantic, quoted engine path]: engine dir whose path contains a space → the backtick command's `--directory` argument is that path as one shell word
- [embed, torch missing, no usable freeze]: `embed.main` with a warehouse file and the same torch `ModuleNotFoundError`, no usable freeze → exit `1`, one stderr line, the pip command, no `Traceback`, no `ensure-env`
- [embed, torch missing, usable freeze]: hashed freeze → exit `1`, one line containing `stockroom shim ensure-env`, not `uv pip install torch`
- [embed, encoder load failure]: `OSError("model download failed")` → exit `1`, one line containing `encoder check failed` and `sr-initialize`, not `ensure-env`
- [embed, other import error]: `ModuleNotFoundError` named `sentence_transformers` → the exception propagates
- [doctor smoke unchanged]: existing `run_smoke` tests still pass after the remedy strings move to the shared functions

### Test Infrastructure

- Framework: pytest (pytest-xdist via the engine `addopts`; override with `-n0` while iterating on one file)
- Test location: `skills/sr-search/tests/`
- Conventions: function tests named `test_*`, docstring states the behavior, `capsys` for stderr, `warehouse_home` isolates `STOCKROOM_HOME`, encoder doubles are plain callables passed as `encoder_factory`
- New test files: none

## Implementation Plan

### 1. [x] Encoder-construction remedy on semantic and embed — executable

- Files: `skills/sr-search/tests/test_semantic.py`, `skills/sr-search/tests/test_embed.py`, `skills/sr-search/src/stockroom/embed.py`, `skills/sr-search/src/stockroom/semantic.py`, `skills/sr-search/src/stockroom/doctor.py`

1. Stub tests: add empty `test_cli_torch_missing_without_freeze_names_pip_remedy`, `test_cli_torch_missing_with_freeze_names_ensure_env`, `test_cli_torch_missing_with_unusable_freeze_names_pip_remedy`, `test_cli_encoder_load_failure_names_repick`, `test_cli_other_import_error_propagates`, and `test_cli_torch_remedy_quotes_engine_path` in `test_semantic.py`. Add empty `test_cli_torch_missing_without_freeze_names_pip_remedy`, `test_cli_torch_missing_with_freeze_names_ensure_env`, `test_cli_encoder_load_failure_names_repick`, and `test_cli_other_import_error_propagates` in `test_embed.py`. Docstrings state the behaviors above.
2. Stub interface: in `embed.py`, add `missing_torch_remedy(app_dir: Path) -> str`, `encoder_load_remedy() -> str`, and `encoder_construction_error(exc: BaseException) -> str | None`, with docstrings and empty bodies (`return ""` / `return None`).
3. Write tests and run red: fill the stubs. Each CLI test creates a warehouse with `warehouse.open(read_only=False)` so construction is reached, passes the raising factory, and asserts the exit code and the single stderr line. The propagate tests use `pytest.raises`. Run the new tests and confirm they fail.
4. Write code and run green: implement the three functions in `embed.py`. `missing_torch_remedy` uses `read_freeze_path()` and `shlex.quote` on the engine path, with the same words `run_smoke` prints today. `encoder_load_remedy` is the re-pick sentence `run_smoke` prints today. `encoder_construction_error` returns `None` for a `ModuleNotFoundError` whose `name` is not `torch` and does not start with `torch.`; for torch it returns `error: torch is not installed in the engine environment at {app_dir} — {missing_torch_remedy(app_dir)}` using `default_app_dir()`; for any other `Exception` it returns `error: encoder check failed ({type}: {exc}) — {encoder_load_remedy()}`. `semantic.main` and `embed.main` wrap only the `encoder_factory()` call: on `Exception`, print the line and return `1`, or re-raise when the line is `None`. `doctor.run_smoke` calls the same two remedy functions inside its existing `fail` so the words cannot drift. Run the new tests, then the existing `test_doctor.py` smoke tests.

### 2. [x] Agent text and the torch page — prose/policy

- Files: `skills/sr-semantic/SKILL.md`, `skills/sr-search/references/system-model.md`, `docs/user-guide/troubleshooting/torch.md`
- No tests: prose/policy artifact

1. In `skills/sr-semantic/SKILL.md`, replace the `ModuleNotFoundError: No module named 'torch'` row with two rows that match the new stderr prefixes. The missing-import row says: run the command in the line (`stockroom shim ensure-env` when that is what it prints; `sr-initialize` when the line is the pip command because there is no usable freeze). The encoder-load row says: re-run `sr-initialize` and pick a different wheel. Both say not to retry the query. Exit code `1`.
2. In `skills/sr-search/references/system-model.md`, replace the sentence that says the only fix is re-running `sr-initialize` with the same three-way split.
3. In `docs/user-guide/troubleshooting/torch.md`, make "Semantic search or embed fails citing torch / environment" state that split, and remove the disagreement in "`stockroom semantic` fails with missing torch" by folding that heading into the same section. Leave the `doctor smoke` heading as the pointer at the same remedies.

## Technology Validation

No new technology - validation not required

## Dependencies

- `stockroom.torch_source.read_freeze_path` (usable hashed freeze)
- `stockroom.shim.default_app_dir` (engine path in the pip remedy)
- Existing `doctor.run_smoke` wording, which the shared functions must keep

## Challenges & Mitigations

- Wrapping more than `encoder_factory()` would turn a search-time bug into a wheel remedy. The `try` covers only that call.
- A non-torch `ModuleNotFoundError` (locked dep such as `sentence_transformers`) must not be labeled a torch problem. `encoder_construction_error` returns `None` and the caller re-raises. A test pins this on both CLIs.
- `embed.py` importing `doctor.py` cycles (`doctor` imports `BgeEncoder` at import time). The functions live in `embed.py`, which `doctor` and `semantic` already import.
- An `ImportError` from a broken torch binary is not a `ModuleNotFoundError`, so it takes the re-pick line rather than `ensure-env`. Accepted: construction is one call, and re-pick still names a real next step. The incident's failure is `ModuleNotFoundError` named `torch`.
- The skill row that matches today's traceback will not match the new line. The new rows match the `error:` prefixes, and the line itself contains the command.

## Pre-Mortem

- CLI-only, leaving the skill's "don't retry; re-run `sr-initialize`" row in place: that row is what the agent obeyed. Step 2 rewrites it. Already the reason option 2 is in the plan, not a substitute for step 1.
- Teaching `ensure-env` for every encoder failure: a bad wheel would be reinstalled from the freeze. The load-failure tests forbid `ensure-env` on that path.
- Two copies of the remedy text: `doctor.run_smoke` is switched onto the same functions in step 1, and its existing tests stay the lock on the words.
- Quoting only the code that runs a shell, and shipping an unquoted path in the printed pip command: the semantic test splits the backtick command with `shlex`, and `doctor`'s existing space/apostrophe test stays on the shared function.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [x] Build
- [ ] QA
