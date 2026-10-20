---
task_id: torch-failures-help
complexity_level: 2
date: 2026-10-20
status: completed
---

# TASK ARCHIVE: torch-failures-help

## SUMMARY

Resolved [#144](https://github.com/Texarkanine/stockroom/issues/144) on `torch-failures-help` / PR [#145](https://github.com/Texarkanine/stockroom/pull/145). When `stockroom semantic` or `stockroom embed` cannot import torch and a usable hashed freeze exists, the command restores that wheel once and retries. A failed restore names the reason and `sr-initialize`. No usable freeze, and any other encoder failure, is one stderr line naming `sr-initialize`. `stockroom doctor smoke` stays report-only.

The first cut of the branch printed a command and exited 1. That overclaimed a repair: the pip line contained a literal `<build>`, and an encoder exception is not automatically a wrong wheel. The rework runs the one restore the freeze already determines.

## REQUIREMENTS

1. A missing torch on `stockroom semantic` and `stockroom embed` must not end as an uncaught traceback.
2. Judge the ticket's options and ship the better design. The ticket's two-way split (freeze means tell the agent to run `stockroom shim ensure-env`, otherwise `sr-initialize`) was not the design that shipped.
3. A usable hashed freeze runs `ensure_engine_env` once, prints `restoring torch from the hashed freeze`, and retries once. A failed restore names its reason and `sr-initialize`, and does not ask anyone to run `ensure-env` again.
4. No usable freeze names `sr-initialize`. It does not print a `uv pip install` line. An encoder exception after torch imports is not treated as a known wheel change.
5. `doctor smoke` does not install. Its usable-freeze line still names `stockroom shim ensure-env`.
6. The `sr-semantic` skill, the torch contract, and the torch page agree. A non-draft pull request is open.

## IMPLEMENTATION

`start_encoder` in `skills/sr-search/src/stockroom/embed.py` builds the encoder. A `ModuleNotFoundError` for `torch` or `torch.*` with a usable freeze prints the restoring line, calls an injected healer (production: `ensure_engine_env`) once with the engine directory, and retries once when the report action is not `failed`. `importlib.invalidate_caches()` runs before that retry. A failed report prints `error: torch restore failed ({reason}) — re-run sr-initialize`. A second construction failure prints `error: encoder check failed ({type}: {exc}) — re-run sr-initialize`. No freeze prints `error: torch is not installed in the engine environment at {app_dir} — re-run sr-initialize (install → smoke → freeze)`. Any other `ModuleNotFoundError` propagates. `semantic.main` and `embed.main` return 1 when `start_encoder` returns `None`.

`missing_torch_remedy` still names `stockroom shim ensure-env` for a usable freeze, which is what smoke prints. Its no-freeze clause is the `sr-initialize` sentence. `encoder_load_remedy` is `re-run sr-initialize`. Smoke does not call the healer.

The catch stays around encoder construction. It is not inside `BgeEncoder`, so smoke and the live constructor tests still see the raw exception.

| Area | Files |
|------|--------|
| Restore | `skills/sr-search/src/stockroom/embed.py`, `semantic.py` |
| Smoke | `skills/sr-search/src/stockroom/doctor.py` |
| Tests | `skills/sr-search/tests/test_semantic.py`, `test_embed.py`, `test_doctor.py`, `test_doctor_cli.py` |
| Agent text | `skills/sr-semantic/SKILL.md`, `skills/sr-search/references/system-model.md` |
| Docs | `docs/user-guide/troubleshooting/torch.md`, `docs/user-guide/load/basic.md` |

## TESTING

- First cut: new CLI tests failed on the uncaught exception, then passed once the shared line was printed. `make ci`: 1018 passed, 38 skipped, ruff clean, reuse compliant.
- Rework: tests inject the healer, so the suite does not pip-install torch. The first pytest run of those tests was already green. The red step was not captured as its own run. `make ci` again: 1018 passed, 38 skipped, 134 dashboard tests, ruff clean, reuse compliant. Exercised on Linux/WSL.
- Preflight of the rework: PASS WITH ADVISORY. Adopted: invalidate import caches before the retry, and retry on any report that is not `failed` (so `noop` retries). Rejected: a generic resilient-env wrapper.
- QA of the first cut: PASS WITH ADVISORY. No test raises `ModuleNotFoundError` named `torch.<submodule>`. That branch is real and unpinned. It is not an acceptance gap.
- QA of the rework: PASS WITH ADVISORY. The four touched test files: 100 passed, 4 torch-gated skips. Neighboring suites (`test_skill_hygiene.py`, `test_engine_env.py`, `test_torch_source.py`): 23 passed. No code change. Advisories: one clause in `system-model.md` says the embed connection stays read-only, which does not fit embed's later read-write open; the new test helpers are duplicated the way this suite already duplicates helpers; the retry-still-fails test exists only on semantic, which is the shared function.

## LESSONS LEARNED

- The agent followed the skill row that matched the traceback, not the troubleshooting page. A remedy that lives only in the docs does not reach that agent.
- Whether a freeze exists is the wrong key for every encoder failure. The freeze chooses a wheel, so it is a determined restore only when torch itself cannot be imported. Naming `stockroom shim ensure-env` for that case was the right diagnosis and the wrong delivery: the command can run the restore. The no-freeze line and the encoder-exception line were guesses.

## PROCESS IMPROVEMENTS

The rework's tests were written before the restore behavior, and the first run of them was already green. A captured red run is the evidence the pins were aimed at the new behavior. QA still treated the assertions as real pins.

## TECHNICAL IMPROVEMENTS

One clause in `skills/sr-search/references/system-model.md` says the embed connection stays read-only. The restore happens before either command opens the warehouse, and embed later opens read-write. The restore writes the engine environment, not the warehouse. That clause can be corrected in a later edit. No other architecture change is waiting.

## NEXT STEPS

PR [#145](https://github.com/Texarkanine/stockroom/pull/145) is open and not a draft. Review and merge are the remaining delivery. The `system-model.md` clause above is a wording fix, not a blocker.
